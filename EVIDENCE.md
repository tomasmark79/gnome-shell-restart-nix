# Verified results

The longer hardware trial exposed two additional defects and a separate
background-pointer regression; see the [incident report](INCIDENT-2026-10-21.md).
Historical passes below did not exercise physical desktop right-clicks. The
current VM test includes actual QEMU pointer input before and after replacement
and after authentication, and requires a single live background group.

The latest [run-dialog verification](evidence/2026-10-21-run-dialog.json) adds
two physical **Alt+F2 → r → Enter** requests among five native VM replacements.
All five preserve clients and custom shortcuts; lock/authentication, subsequent
client input, the 65-second observation and retired-callback checks also pass.
The first keyboard attempt sent input before dialog opening completed; the
repeatable test now waits for the open dialog, entry focus and actual typed text.
This change has not been activated or exercised on the personal desktop.

Validated on 2026-10-21 for GNOME Shell/Mutter 50.5 and GJS 1.88.1.

A public, redacted [evidence summary](evidence/2026-10-21.json) includes the
automated report hashes and tested source hashes. Raw test reports are generated
locally by the commands below; they are not bundled. Extension display strings
were clarified for publication after testing; executable behavior is unchanged.

| Check | Result |
| --- | --- |
| Extracted workspace headless end-to-end | Passed, 5 complete context replacements |
| Original Mutter identity and original Wayland/XWayland sockets | Preserved across all replacements |
| Client state before input, post-recovery input and new client windows | Passed |
| Panel menus, window menu and keyboard-driven overview | Passed |
| Delayed observation | 65 seconds; no transition diagnostics |
| Old contexts | 5 finalized; all retired callback ledger entries empty |
| Repeated native types and vfunc dispatchers | 989 types / 229 dispatchers, unchanged across all 5 desktop cycles |
| Native ownership, gap dispatch and child reaping | Passed directly and under Valgrind |
| Native-backend VM, CLI and Alt+F2 `r` command | Passed, 5 complete replacements; 2 triggered through the run dialog |
| Real custom Super+T shortcut | Passed before replacement and after each of 5 replacements; same media-key daemon |
| Login PATH / Console application discovery | System profile retained; Console visible |
| Negative control without external accelerator restoration | Expected failure: custom shortcut stops after first replacement |
| Actual logind lock, wrong password rejection and GDM/PAM unlock | Passed after complete context replacement |
| Physical VM keyboard input to both original clients after unlock | Passed; original connections retained |
| Native-backend package and disabled-by-default NixOS module | Built / evaluated for GNOME 50.5 |
| CLI safety checks | 12 passed |
| Updated candidate on physical desktop | One complete replacement; same compositor PID; all 7 windows and positions preserved |
| Hardware custom shortcuts | User confirmed all personal shortcuts work after replacement |

Desktop evidence is `artifacts/run-dialog-headless/result.json`. Native
control evidence is `artifacts/native-control.json`. Both are generated,
ignored by Git and reproduced by the README commands.

The native-backend VM result is stored at:

```text
/nix/store/8yfrsajrz38x4l9f6zhm669drpkwdam8-vm-test-run-tgnome-full-context/evidence/tgnome-evidence/result.json
```

Its `passed`, `originalObjectiveAchieved`, `explicitNativeBackend` and
`wrongPasswordRejected` fields are true; `diagnosticProblems` is empty.
`securityVm` is false: this run exercises the explicit native-backend opt-in
of the publication candidate rather than the research VM-only admission gate.
The command used by the VM is the packaged user command, not a synthetic reset.

Recheck the saved evidence and produce its SHA-256/source manifest:

```sh
vm=$(nix build --no-link --print-out-paths .#full-context-desktop-vm)
python3 tests/verify-results.py \
  --desktop artifacts/pointer-fixed-headless/result.json \
  --native artifacts/incident-native-control-2.json \
  --vm "$vm/evidence/tgnome-evidence/result.json"
```

For a fresh run, build `.#full-context-native-vm` with `--print-out-paths` and
use that output's `evidence/tgnome-evidence/result.json`. The generated
`artifacts/verification.json` records the checked evidence and source hashes.

The original research checkout additionally preserves independent clean
desktop runs and a separate successful GDM/PAM/logind VM run. The existing UI
reconstruction fallback and its earlier acceptance evidence remain separate.

A personal trial of the earlier candidate preserved applications through user
restarts but exposed missing applications and custom shortcuts. On that host,
changing only the PATH in a standalone Gio application scan changed visible
applications from 17 to 129 and restored Console discovery. The updated module
inherits the login PATH. That observation is separate from the isolated VM's
automated application-discovery assertion.

Reproduce the accelerator negative control with:

```sh
nix build --no-link --keep-failed .#full-context-shortcuts-negative-vm
```

This deliberately disables only routing restoration and is expected to fail
waiting for the custom shortcut after the first replacement. The passing VM
uses the identical fixture with restoration enabled. Test evidence verifies
Super+T routing using a marker command. After the user activated the updated
candidate and logged in again, the agent issued exactly one successful reset.
Its runtime epoch changed, `contextsFinalized` advanced from 0 to 1, Mutter's
PID stayed unchanged, and the seven original window IDs and frames matched.
The panel was present once, startup completed, and the retired runtime's native
callback ledger was empty. The user then confirmed that all personal shortcuts
worked. This manual confirmation is not an automated test of each shortcut.
The retired D-Bus callback leak observed in the earlier hardware trial is absent
in both this updated hardware snapshot and the five-cycle isolated tests.

The hardware snapshot does not independently measure each application's client
socket or exercise input into every application. Those checks are automated in
the isolated tests. Private desktop titles, screenshots and raw host logs are
intentionally excluded from the public repository.

These results establish cooperative complete runtime replacement in the
specified isolated environments. They do not establish recovery of a hung
runtime, lock arrival during replacement or general real-hardware support.
