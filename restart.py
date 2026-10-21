"""User-invoked restart of the explicitly installed patched Shell session."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
    sys.exit('An explicit session bus is required')
owner = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.freedesktop.DBus',
    '--object-path', '/org/freedesktop/DBus', '--method',
    'org.freedesktop.DBus.GetNameOwner', 'org.gnome.Shell'],
    check=True, text=True, capture_output=True, timeout=5)
os.environ['TGNOME_BUS_OWNER'] = ast.literal_eval(owner.stdout.strip())[0]
os.environ['TGNOME_REBIND_TYPES'] = '1'
os.environ['TGNOME_ALLOW_RUNTIME_RESET'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Nix stores individual source files separately, so the entry point is passed
# through an explicit environment variable by the package wrapper.
import runpy
namespace = runpy.run_path(os.environ['TGNOME_CLI_SOURCE'])
try:
    print(json.dumps(namespace['restart_shell_context']()))
except RuntimeError as error:
    sys.exit(str(error))
