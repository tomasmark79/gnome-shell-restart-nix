"""Complete-context replacement with real guest GDM, PAM and logind."""
import ast
import json
import shlex
import time
from typing import Any, cast


def alice(command):
    return ('runuser -u alice -- env XDG_RUNTIME_DIR=/run/user/1000 '
            'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus ' + command)


def evaluate(js):
    raw = machine.succeed(alice('gdbus call --session --dest org.gnome.Shell '
        '--object-path /org/gnome/Shell --method org.gnome.Shell.Eval ' + shlex.quote(js))).strip()
    ok, quoted = raw[1:-1].split(',', 1)
    assert ok == 'true', raw
    return json.loads(ast.literal_eval(quoted.strip()))


def wait_value(js, predicate, timeout=90):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = evaluate(js)
            if predicate(last):
                return last
        except (AssertionError, ValueError) as error:
            last = str(error)
        time.sleep(0.5)
    raise AssertionError(f'Shell condition timed out: {js}: {last}')


def native():
    raw = machine.succeed(alice('gdbus call --session --dest org.gnome.Shell '
        '--object-path /org/gnome/Shell/TgnomeRuntime '
        '--method org.gnome.Shell.TgnomeRuntime.Status'))
    return json.loads(ast.literal_eval(raw.strip())[0])


def extension_call(method):
    raw = machine.succeed(alice('gdbus call --session --dest org.gnome.Shell '
        '--object-path /org/gnome/Shell/Extensions/Tgnome '
        '--method org.gnome.Shell.Extensions.Tgnome.' + method))
    return json.loads(ast.literal_eval(raw.strip())[0])


def check_dash():
    if not desktop_integration:
        return None
    return wait_value("Main.extensionManager.lookup('dash-to-dock@micxgx.gmail.com')?.state",
                      lambda state: state == 1, timeout=20)


def check_background_pointer():
    setup = evaluate('''(() => {
        global._tgnomePointerWindows = global.get_window_actors()
            .map(a=>a.meta_window).filter(w=>!w.minimized);
        for(const w of global._tgnomePointerWindows) w.minimize();
        const m=Main.layoutManager.monitors[0];
        global._tgnomePointerEvents=[];
        global._tgnomePointerCapture=global.stage.connect('captured-event', (_s,e)=>{
            if(e.type()===imports.gi.Clutter.EventType.BUTTON_PRESS ||
               e.type()===imports.gi.Clutter.EventType.BUTTON_RELEASE)
                global._tgnomePointerEvents.push({type:e.type(),button:e.get_button(),coords:e.get_coords()});
            return imports.gi.Clutter.EVENT_PROPAGATE;
        });
        return {x:Math.floor(m.width*.75),y:Math.floor(m.height*.6),width:m.width,height:m.height};
    })()''')
    time.sleep(0.5)
    try:
        assert machine.qmp_client is not None
        qmp = cast(Any, machine.qmp_client)
        qmp.send('input-send-event', {'events': [
            {'type':'abs','data':{'axis':'x','value':round(setup['x']*32767/(setup['width']-1))}},
            {'type':'abs','data':{'axis':'y','value':round(setup['y']*32767/(setup['height']-1))}},
        ]})
        time.sleep(0.2)
        qmp.send('input-send-event', {'events':[
            {'type':'btn','data':{'down':True,'button':'right'}}]})
        time.sleep(0.1)
        qmp.send('input-send-event', {'events':[
            {'type':'btn','data':{'down':False,'button':'right'}}]})
        time.sleep(0.5)
        state = evaluate('''(() => {
            const a=Main.layoutManager._bgManagers[0].backgroundActor;
            const [x,y]=global.get_pointer();
            const picked=global.stage.get_actor_at_pos(imports.gi.Clutter.PickMode.REACTIVE,x,y);
            return {opened:a._backgroundMenu.isOpen,mapped:a._backgroundMenu.actor.mapped,
                pointer:[x,y],picked:picked?.toString(),pickedIsCurrentBackground:picked===a,
                backgroundGroups:global.window_group.get_children().filter(a=>a instanceof imports.gi.Meta.BackgroundGroup).length,
                events:global._tgnomePointerEvents,
                actions:a.get_actions().map(a=>({type:a.constructor.name,enabled:a.enabled}))};
        })()''')
        report['lastBackgroundPointerAttempt'] = state
        assert state['opened'] and state['mapped'] and state['pickedIsCurrentBackground'], state
        assert state['backgroundGroups'] == 1, state
        return state
    finally:
        machine.send_key('esc')
        evaluate('''(() => {
            global.stage.disconnect(global._tgnomePointerCapture);
            for(const w of global._tgnomePointerWindows) w.unminimize();
            return true;
        })()''')


def churn_stylesheets():
    return evaluate('''(() => {
        const {Gio,GLib,St}=imports.gi;
        const path='/home/alice/tgnome-lifetime.css';
        GLib.file_set_contents(path,'.tgnome-fixture { color: red; }');
        const file=Gio.File.new_for_path(path);
        const theme=St.ThemeContext.get_for_stage(global.stage).get_theme();
        for(let n=0;n<20;n++) {
            theme.load_stylesheet(file); theme.load_stylesheet(file);
            theme.unload_stylesheet(file);
            if(theme.get_custom_stylesheets().some(f=>!f || f.equal(file)))
                throw Error('Stale custom stylesheet after unload');
        }
        Main.loadTheme(); GLib.unlink(path);
        return {cycles:20,validCustomStylesheets:true};
    })()''')


def client_record(backend):
    return json.loads(machine.succeed(f'tail -n 1 /home/alice/{backend}.jsonl'))


def check_custom_shortcut(expected):
    machine.send_key('meta_l-t')
    machine.wait_until_succeeds(
        f'test -f /home/alice/tgnome-shortcuts.log && '
        f'test $(wc -l < /home/alice/tgnome-shortcuts.log) -eq {expected}', timeout=10)
    return expected


def clients_unchanged():
    result = {b: client_record(b) for b in initial}
    for backend, old in initial.items():
        new = result[backend]
        assert all(new[k] == old[k] for k in
                   ('pid', 'backend', 'fd', 'inode', 'windowId', 'unsavedTextSha256')), (old, new)
        assert new['tick'] > old['tick']
    return result


STATE = '''({pid:new imports.gi.Gio.Credentials().get_unix_pid(),
    epoch:global._tgnomeRuntimeEpoch,locked:Main.screenShield.locked,
    active:Main.screenShield.active,mode:Main.sessionMode.currentMode,
    session:Main.screenShield._loginSession?.Id ?? null,
    starting:Main.layoutManager._startingUp})'''

start_all()
report: dict[str, object] = {'passed': False, 'originalObjectiveAchieved': False, 'cycles': [],
          'classification': 'COMPLETE SHELL CONTEXT REPLACEMENT'}
try:
    desktop_integration = machine.succeed('cat /etc/tgnome-desktop-integration').strip() == '1'
    report['desktopIntegration'] = desktop_integration
    machine.wait_for_unit('display-manager.service', timeout=180)
    machine.wait_for_file('/run/user/1000/wayland-0', timeout=180)
    machine.wait_for_unit('default.target', 'alice', timeout=180)
    before = wait_value(STATE, lambda s: not s['starting'] and s['session'])
    assert not before['locked'] and before['mode'] == 'user'
    session = shlex.quote(before['session'])
    assert machine.succeed(f'loginctl show-session {session} -p Type --value').strip() == 'wayland'
    report['before'] = before
    report['pathHasSystemProfile'] = evaluate(
        'imports.gi.GLib.getenv("PATH").split(":").includes("/run/current-system/sw/bin")')
    assert report['pathHasSystemProfile']
    report['consoleVisibleBefore'] = evaluate(
        'imports.gi.Gio.AppInfo.get_all().some(a => '
        'a.get_id() === "org.gnome.Console.desktop" && a.should_show())')
    assert report['consoleVisibleBefore']
    native_backend = evaluate('imports.gi.GLib.getenv("TGNOME_ALLOW_NATIVE_CONTEXT_RESET") === "1"')
    assert native()['securityVm'] is True or native_backend
    report['explicitNativeBackend'] = native_backend
    machine.succeed(alice('gnome-extensions enable restart-island@tgnome.local'))
    wait_value("Main.extensionManager.lookup('restart-island@tgnome.local')?.state === 1", bool)
    # Establish the desktop's real client workload before checking Shell input.
    for backend in ('wayland', 'x11'):
        machine.succeed(alice(f'systemd-run --user --unit=tgnome-probe-{backend} '
            f'--property=StandardOutput=append:/home/alice/{backend}.jsonl '
            f'--property=StandardError=append:/home/alice/{backend}.log '
            f'--setenv=GDK_BACKEND={backend} --setenv=NO_AT_BRIDGE=1 '
            '--setenv=GTK_A11Y=none tgnome-client-probe'))
        machine.wait_until_succeeds(f'test -s /home/alice/{backend}.jsonl')
    wait_value('!Main.overview.animationInProgress', bool)
    machine.send_key('esc')
    time.sleep(0.3)
    report['initialUi'] = evaluate('({overview:Main.overview.visible,modal:Main.modalCount,'
        'mode:Main.actionMode,focus:global.stage.key_focus?.constructor.name ?? null})')
    if desktop_integration and report['initialUi']['overview']:
        # Initial setup only. Actual overview keys are checked below and after
        # every reset once the desktop/client workload is established.
        evaluate('(() => { Main.overview.hide(); return true; })()')
        report['initialSetupHideUsed'] = True
    wait_value('Main.overview.visible', lambda visible: not visible, timeout=10)
    report['dashBefore'] = check_dash()
    report['themeBefore'] = churn_stylesheets()
    report['backgroundMenuBefore'] = extension_call('ExerciseBackgroundMenu')
    report['backgroundPointerBefore'] = check_background_pointer()
    report['shortcutBefore'] = check_custom_shortcut(1)
    media_pid_before = machine.succeed(alice(
        'systemctl --user show org.gnome.SettingsDaemon.MediaKeys.service --property=MainPID --value')).strip()
    machine.send_key('meta_l')
    wait_value('Main.overview.visible && !Main.overview.animationInProgress', bool)
    machine.send_key('esc')
    wait_value('Main.overview.visible', lambda visible: not visible)
    initial = {b: client_record(b) for b in ('wayland', 'x11')}
    report['clientsBefore'] = initial
    owner = evaluate('imports.gi.Gio.DBus.session.get_unique_name()')
    cursor = machine.succeed('journalctl -n 0 --show-cursor').strip().split('-- cursor: ')[-1]
    epochs = {before['epoch']}
    # Čtvrtý a pátý restart ověřují překročení původního limitu tří obnov.
    for number in range(1, 6):
        with subtest(f'Complete context replacement {number} with native backend'):
            restart_command = (alice('restart-gnome-shell') if native_backend else alice('env TGNOME_REBIND_TYPES=1 '
                'TGNOME_ALLOW_RUNTIME_RESET=1 TGNOME_BUS_OWNER=' + shlex.quote(owner) +
                ' tgnome restart-shell-context'))
            if native_backend and number in (2, 4):
                previous = evaluate(STATE)
                machine.send_key('alt-f2')
                wait_value('Main.runDialog?.state === 0 && '
                           'global.stage.key_focus === Main.runDialog._entryText', bool)
                assert evaluate('Main.runDialog._enableInternalCommands')
                machine.send_chars('r')
                wait_value('Main.runDialog._entryText.get_text() === "r"', bool)
                machine.send_key('ret')
                try:
                    state = wait_value(STATE, lambda s: not s['starting'] and s['session']
                                       and s['epoch'] not in epochs, timeout=45)
                except AssertionError:
                    report['runDialogFailure'] = evaluate('({text:Main.runDialog?._entryText.get_text(),'
                        'error:Main.runDialog?._descriptionLabel.text,modal:Main.modalCount,'
                        'state:Main.runDialog?.state,enabled:Main.runDialog?._enableInternalCommands})')
                    machine.log(machine.succeed('journalctl -b --no-pager | '
                        'grep -E "PreparationFailed|restart-gnome|TGNOME|Traceback" | tail -n 30'))
                    raise
                command = {'trigger': 'Alt+F2 r Enter',
                           'evidence': 'Observed runtime state after physical VM keyboard input',
                           'wholeShellRestarted': state['epoch'] != previous['epoch'],
                           'compositorPreserved': state['pid'] == previous['pid'],
                           'beforeEpoch': previous['epoch'], 'afterEpoch': state['epoch']}
            else:
                raw = machine.succeed(restart_command)
                command = json.loads(raw)
                command['trigger'] = 'CLI'
                state = wait_value(STATE, lambda s: not s['starting'] and s['session']
                                   and s['epoch'] not in epochs)
            assert state['pid'] == before['pid'] and state['session'] == before['session']
            assert state['epoch'] not in epochs and not state['locked']
            epochs.add(state['epoch'])
            current = native()
            assert current['contextsFinalized'] == number
            dash_state = check_dash()
            background_menu = extension_call('ExerciseBackgroundMenu')
            background_pointer = check_background_pointer()
            theme = churn_stylesheets()
            shortcut_count = check_custom_shortcut(number + 1)
            assert machine.succeed(alice(
                'systemctl --user show org.gnome.SettingsDaemon.MediaKeys.service '
                '--property=MainPID --value')).strip() == media_pid_before
            machine.send_key('meta_l')
            wait_value('Main.overview.visible && !Main.overview.animationInProgress', bool)
            machine.screenshot(f'overview-after-context-{number}')
            machine.send_key('esc')
            wait_value('Main.overview.visible', lambda visible: not visible)
            report['cycles'].append({'command': command, 'state': state,
                                     'dashState': dash_state, 'backgroundMenu': background_menu,
                                     'backgroundPointer': background_pointer,
                                     'theme': theme,
                                     'customShortcutCount': shortcut_count,
                                     'native': current, 'clients': clients_unchanged()})
    with subtest('Real logind lock and PAM authentication after complete replacement'):
        machine.succeed(f'loginctl lock-session {session}')
        locked = wait_value(STATE, lambda s: s['locked'] and s['active'])
        assert locked['pid'] == before['pid']
        machine.wait_until_succeeds(f'test $(loginctl show-session {session} -p LockedHint --value) = yes')
        report['clientsWhileLocked'] = clients_unchanged()
        if not evaluate('!!Main.screenShield._dialog?._authPrompt'):
            machine.send_key('ret')
        wait_value('!!Main.screenShield._dialog?._authPrompt?._entry.reactive', bool)
        wrong_cursor = machine.succeed('journalctl -n 0 --show-cursor').strip().split('-- cursor: ')[-1]
        machine.send_key('ctrl-a')
        machine.send_chars('incorrect-vm-password')
        machine.send_key('ret')
        machine.wait_until_succeeds('journalctl -b --after-cursor=' + shlex.quote(wrong_cursor) +
            " --no-pager | grep -F 'pam_unix(gdm-password:auth): authentication failure'", timeout=30)
        wait_value('!!Main.screenShield._dialog?._authPrompt?._entry.reactive', bool)
        assert evaluate(STATE)['locked']
        report['wrongPasswordRejected'] = True
        machine.send_key('ctrl-a')
        machine.send_chars('tgnome-vm-password')
        machine.send_key('ret')
        after = wait_value(STATE, lambda s: not s['locked'] and not s['active'] and s['mode'] == 'user')
        assert after['pid'] == before['pid'] and after['session'] == before['session']
        machine.wait_until_succeeds(f'test $(loginctl show-session {session} -p LockedHint --value) = no')
        report['afterUnlock'] = after
        report['dashAfterUnlock'] = check_dash()
        report['backgroundMenuAfterUnlock'] = extension_call('ExerciseBackgroundMenu')
        report['backgroundPointerAfterUnlock'] = check_background_pointer()
        report['themeAfterUnlock'] = churn_stylesheets()
        report['clientsAfterUnlock'] = clients_unchanged()
        machine.screenshot('desktop-after-context-replacement-and-unlock')
    time.sleep(65)
    report['clientsAfterObservation'] = clients_unchanged()
    report['nativeKeyboardInput'] = {}
    for backend, old in initial.items():
        evaluate("(() => { const w = global.get_window_actors().map(a => a.meta_window)"
                 f".find(w => w.get_pid() === {old['pid']}); Main.activateWindow(w); return true; }})()")
        time.sleep(0.2)
        machine.send_key('end')
        machine.send_chars('a')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            typed = client_record(backend)
            if typed['unsavedTextSha256'] == typed['expectedTypedSha256']:
                break
            time.sleep(0.2)
        assert typed['unsavedTextSha256'] == typed['expectedTypedSha256'], typed
        assert all(typed[k] == old[k] for k in ('pid', 'backend', 'fd', 'inode', 'windowId'))
        report['nativeKeyboardInput'][backend] = typed
    final = native()
    report['nativeFinal'] = final
    callbacks = final['callbacks']
    retired = {e: names for e, names in callbacks['epochs'].items()
               if int(e) < callbacks['latestEpoch'] and names}
    assert not retired, retired
    journal = machine.succeed(f"journalctl -b _PID={before['pid']} --after-cursor=" +
                              shlex.quote(cursor) + ' --no-pager -o cat')
    problems = [line for line in journal.splitlines() if any(text in line for text in
        ('JS ERROR', 'already disposed', 'Exception in callback', 'CRITICAL', 'runtime startup failed'))]
    report['diagnosticProblems'] = problems
    assert not problems, problems
    report['passed'] = report['originalObjectiveAchieved'] = True
finally:
    print('TGNOME_FULL_CONTEXT_RESULT=' + json.dumps(report))
    machine.succeed('mkdir -p /tmp/tgnome-evidence')
    payload = shlex.quote(json.dumps(report, indent=2))
    machine.succeed(f"printf '%s\\n' {payload} > /tmp/tgnome-evidence/result.json")
    machine.succeed('journalctl -b --no-pager > /tmp/tgnome-evidence/journal.log')
    machine.succeed('cp /home/alice/*.jsonl /home/alice/*.log /tmp/tgnome-evidence/ 2>/dev/null || true')
    machine.copy_from_machine('/tmp/tgnome-evidence', 'evidence')
