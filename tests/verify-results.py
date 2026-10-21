"""Verify and fingerprint the saved end-to-end evidence without rerunning it."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--desktop', type=Path, required=True)
parser.add_argument('--native', type=Path, required=True)
parser.add_argument('--vm', type=Path, required=True)
parser.add_argument('--output', type=Path, default=Path('artifacts/verification.json'))
args = parser.parse_args()
desktop, native, vm = (json.loads(p.read_text()) for p in (args.desktop, args.native, args.vm))
assert desktop['passed'] and desktop['originalObjectiveAchieved']
proof = desktop['fullContextRecovery']
assert len(proof['cycles']) >= 5 and proof['observationSeconds'] >= 65
assert not proof['diagnosticProblems'] and not proof['retiredCallbacks']
assert proof['repeatableExecutionVerified'] and desktop['supervisor']['privateProfileRemoved']
epochs = {proof['cycles'][0]['beforeEpoch']}
for number, cycle in enumerate(proof['cycles'], 1):
    assert cycle['afterEpoch'] not in epochs
    epochs.add(cycle['afterEpoch'])
    assert cycle['native']['contextsFinalized'] == number
    assert cycle['native']['pid'] == desktop['shellBefore']['pid']
    assert cycle['command']['wholeShellRestarted']
    assert cycle['overview']['opened'] and cycle['overview']['closed']
    for backend, original in ((b, desktop[b]['before']) for b in ('wayland', 'x11')):
        current = cycle['clients'][backend]
        assert all(current[k] == original[k] for k in
                   ('pid', 'fd', 'inode', 'windowId', 'unsavedTextSha256'))
for key in ('registeredObjectTypes', 'vfuncBridges'):
    assert len({c['native'][key] for c in proof['cycles']}) == 1
assert set(proof['lateClients']) == set(proof['input']) == {'wayland', 'x11'}
for value in proof['input'].values():
    assert value['after']['unsavedTextSha256'] == value['after']['expectedTypedSha256']
assert native['passed'] and {c['mode'] for c in native['cases']} == {'native', 'valgrind'}
for case in native['cases']:
    assert case['passed'] and not case['stderr'].strip()
    events = [e for e in case['events'] if 'generation' in e]
    assert len(events) == 3 and all(e['released'] and e['nativeChildReaped'] for e in events)
assert vm['passed'] and vm['originalObjectiveAchieved'] and vm['explicitNativeBackend']
assert vm['wrongPasswordRejected'] and not vm['diagnosticProblems']
assert len(vm['cycles']) >= 5
assert sum(c['command'].get('trigger') == 'Alt+F2 r Enter' for c in vm['cycles']) >= 2
assert vm['before']['pid'] == vm['nativeFinal']['pid'] == vm['afterUnlock']['pid']
assert vm['nativeFinal']['contextsFinalized'] == len(vm['cycles'])
assert vm['pathHasSystemProfile'] and vm['consoleVisibleBefore']
assert vm['shortcutBefore'] == 1
assert all(c['customShortcutCount'] == i + 1 for i, c in enumerate(vm['cycles'], 1))
assert set(vm['nativeKeyboardInput']) == {'wayland', 'x11'}
for backend, current in vm['nativeKeyboardInput'].items():
    original = vm['clientsBefore'][backend]
    assert all(current[k] == original[k] for k in ('pid', 'fd', 'inode', 'windowId'))
    assert current['unsavedTextSha256'] == current['expectedTypedSha256']
callbacks = vm['nativeFinal']['callbacks']
assert not any(names for epoch, names in callbacks['epochs'].items()
               if int(epoch) < callbacks['latestEpoch'])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path(__file__).resolve().parents[1]
sources = [root / name for name in ('flake.nix', 'flake.lock', 'packages.nix',
                                  'module.nix', 'tgnome.py', 'restart.py')]
for directory in ('shell', 'extension', 'tests'):
    sources.extend(p for p in (root / directory).iterdir() if p.is_file())
result = {'passed': True, 'originalObjectiveAchieved': True,
          'completeRuntimeReplacementVerified': True, 'hostActivationPerformed': False,
          'desktopCycles': len(proof['cycles']), 'nativeVmCycles': len(vm['cycles']), 'observationSeconds': 65,
          'evidenceSha256': {str(p): digest(p) for p in (args.desktop, args.native, args.vm)},
          'sourceSha256': {str(p.relative_to(root)): digest(p) for p in sorted(sources)}}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(f'passed=True; complete runtime replacement verified; {args.output}')
