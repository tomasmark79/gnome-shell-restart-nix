"""Apply changes restricted to the complete-context Shell build."""
from pathlib import Path


def replace(path, old, new):
    source = Path(path).read_text()
    assert source.count(old) == 1, (path, old, source.count(old))
    Path(path).chmod(Path(path).stat().st_mode | 0o200)
    Path(path).write_text(source.replace(old, new))


replace('js/ui/init.js', '            let removed = 0;',
        '            tgnomeReleaseNativeWork();\n            let removed = 0;')
# The compositor-owned window_group survives a reset. Background groups are
# Shell UI children of that group, outside uiGroup; upstream only tears them
# down on process exit. Retaining them leaves a dead reactive background above
# the newly inserted group, intercepting pointer input after the first reset.
replace('js/ui/layout.js',
        '''            this._destroyHotCorners();
            this._destroyPanelBarrier();
            this.uiGroup.destroy();''',
        '''            this._bgLoadCancellable?.cancel();
            this._bgLoadCancellable = null;
            for (const manager of this._bgManagers)
                manager.destroy();
            this._bgManagers = [];
            this._backgroundGroup.destroy();
            this._destroyHotCorners();
            this._destroyPanelBarrier();
            this.uiGroup.destroy();''')
replace('src/tgnome-runtime.h', 'static gboolean tgnome_probe_allowed;',
        '''extern char *gjs_tgnome_callback_lifetimes (void);
extern unsigned gjs_tgnome_rebind_bridge_count (void);
static gboolean tgnome_probe_allowed;''')
replace('src/tgnome-runtime.h',
        '  g_autofree char *new_types = tgnome_new_object_types ();',
        '''  g_autofree char *callbacks = gjs_tgnome_callback_lifetimes ();
  g_autofree char *new_types = tgnome_new_object_types ();''')
replace('src/tgnome-runtime.h',
        '"{\\\"pid\\\":%d,\\\"publishedUiGeneration\\\":%d,\\\"attempts\\\":%u,\\\"contextsFinalized\\\":%u,"',
        '"{\\\"callbacks\\\":%s,\\\"vfuncBridges\\\":%u,\\\"pid\\\":%d,\\\"publishedUiGeneration\\\":%d,\\\"attempts\\\":%u,\\\"contextsFinalized\\\":%u,"')
replace('src/tgnome-runtime.h', '                          (int) getpid (), published_generation,',
        '                          callbacks, gjs_tgnome_rebind_bridge_count (), (int) getpid (), published_generation,')
# Úplná obnova nemá početní limit; omezení samostatných laboratorních variant zůstávají.
replace('src/tgnome-runtime.h',
        '''      if (tgnome_probe_attempts >= (in_place ? 3u : 1u))
        {
          g_dbus_method_invocation_return_error (invocation, G_IO_ERROR,
            G_IO_ERROR_NOT_SUPPORTED, "Laboratory attempt limit reached; Only one laboratory reset is permitted per context probe");
          return;
        }
''', '')
replace('src/tgnome-runtime.h', 'tgnome_runtime_reset_idle (gpointer data)\n{',
        '''tgnome_runtime_reset_idle (gpointer data)
{
  // A nested main-loop iteration may still be on a GJS evaluation stack.
  // Destruction must happen only from Mutter's outer native dispatch loop.
  if (g_main_depth () > 1)
    {
      g_timeout_add_full (G_PRIORITY_LOW, 10, tgnome_runtime_reset_idle, NULL, NULL);
      return G_SOURCE_REMOVE;
    }''')
# Unlike stable UI recovery, whole-context Status must never enter JS or spin
# its nested main loop. The complete-context build has no UI security curtain.
source = Path('src/tgnome-runtime.h').read_text()
begin = source.index('  if (tgnome_security_vm)', source.index('tgnome_runtime_status (void)'))
end = source.index('  return g_strdup_printf', begin)
assert '_tgnomeGetSecurityBoundary' in source[begin:end]
Path('src/tgnome-runtime.h').write_text(source[:begin] + source[end:])
replace('js/ui/focusCaretTracker.js',
        '        this._atspiListener = Atspi.EventListener.new(this._onChanged.bind(this));',
        '''        (global._tgnomeFocusTrackers ??= new Set()).add(this);
        this._atspiListener = global.tgnome_get_focus_listener();
        this._tgnomeListenerSignal = this._atspiListener.connect(
            'tgnome-focus-event', (_listener, event) => this._onChanged(event));''')
replace('src/shell-global.h', 'G_END_DECLS',
        '''GObject *shell_global_tgnome_get_focus_listener (ShellGlobal *global);
const char *shell_global_tgnome_get_external_accelerators (ShellGlobal *global);
void shell_global_tgnome_set_external_accelerators (ShellGlobal *global, const char *records);

G_END_DECLS''')
replace('js/ui/shellDBus.js', '        this._grabbers = new Map();',
        '        this._grabbers = new Map();\n        tgnomeRestoreExternalAccelerators(this);')
# GNOME 50 no longer includes the historical Xorg "r" command. Restore that
# spelling only in this patched build, using the guarded external controller.
# Default GLib child reaping avoids leaving a JS child-watch in the old runtime.
replace('js/ui/runDialog.js',
        "            'lg': () => Main.createLookingGlass().open(),",
        """            'r': () => {
                try {
                    GLib.spawn_async(null, ['restart-gnome-shell'], null,
                        GLib.SpawnFlags.SEARCH_PATH, null);
                } catch (error) {
                    this._showError(error.message);
                }
            },
            'lg': () => Main.createLookingGlass().open(),""")
replace('src/meson.build', 'gnome_shell_deps = [',
        "gnome_shell_deps = [\n  dependency('atspi-2'),")
# Reloads and failed extension enable paths may load an already active file.
# A duplicate list entry otherwise survives unload after its GFile map entry is
# removed, and Main.loadTheme() later receives a null custom stylesheet.
replace('src/st/st-theme.c',
        '  stylesheet = resolve_stylesheet (theme, file, error);',
        '''  stylesheet = g_hash_table_lookup (theme->stylesheets_by_file, file);
  if (stylesheet && g_slist_find (theme->custom_stylesheets, stylesheet))
    return TRUE;

  stylesheet = resolve_stylesheet (theme, file, error);''')
replace('js/misc/ibusManager.js',
        '''            GLib.child_watch_add(
                GLib.PRIORITY_DEFAULT,
                pid,
                () => GLib.spawn_close_pid(pid)
            );''',
        '''            imports._gi.tgnome_watch_child(GLib.PRIORITY_DEFAULT, pid);''')
