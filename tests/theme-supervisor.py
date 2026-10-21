"""Run the St.Theme regression without any connection to the active desktop."""
import json
import os
from pathlib import Path
import subprocess
import sys

shell = Path(sys.argv[1]).resolve()
if shell.name == 'gnome-shell' and shell.parent.name == 'bin':
    shell = shell.parent.parent
closure = subprocess.check_output(['nix-store', '-qR', str(shell)], text=True).splitlines()
directories = [shell / 'lib/gnome-shell']
gjs = None
for name in closure:
    root = Path(name)
    directory = root / 'lib/girepository-1.0'
    if directory.exists():
        directories.append(directory)
    if '-mutter-' in name:
        directories.extend(path.parent for path in root.rglob('Meta-*.typelib'))
    if '-tgnome-type-rebind-gjs-' in name and (root / 'bin/gjs').exists():
        gjs = root / 'bin/gjs'
if gjs is None:
    raise SystemExit('Matching private GJS not found in the selected Shell closure')
env = dict(os.environ)
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'G_DEBUG'):
    env.pop(key, None)
env.update(GI_TYPELIB_PATH=':'.join(map(str, directories)),
           LD_LIBRARY_PATH=':'.join(map(str, directories)),
           DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/tgnome-no-session-bus',
           DBUS_SYSTEM_BUS_ADDRESS='unix:path=/tmp/tgnome-no-system-bus')
result = subprocess.run([str(gjs), str(Path(__file__).with_name('theme-lifetime.js'))],
                        env=env, capture_output=True, text=True, timeout=20)
report = {'passed': result.returncode == 0 and not result.stderr.strip(),
          'shell': str(shell), 'exitCode': result.returncode,
          'stdout': result.stdout, 'stderr': result.stderr,
          'privateBuslessProcess': True}
print(json.dumps(report, indent=2))
sys.exit(0 if report['passed'] else 1)
