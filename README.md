# GNOME Shell restart for NixOS

An experimental patch that replaces the entire Shell JavaScript runtime while
keeping the same Mutter process and existing Wayland and XWayland connections.
Pinned versions: GNOME Shell/Mutter 50.5, GJS 1.88.1, SpiderMonkey 140, x86_64-linux.
This is an independent experiment, not an official GNOME feature.

Five complete replacements passed in the latest isolated desktop and native VM
tests, including a custom Super+T shortcut before and after each VM replacement.
Three complete replacements also passed in each of two earlier private desktop
tests, including client socket identity, unsaved text, post-restart input,
keyboard-driven overview, menus, new windows and 65 seconds of observation.
Old contexts finalized; retired native callback counts reached zero. The
extracted workspace also passed its desktop test and a native-backend VM test
using the packaged `restart-gnome-shell` command. The VM verifies real
GDM/PAM/logind lock/unlock and keyboard input into both original clients after
replacement. A subsequent hardware trial completed one replacement, preserved
all seven existing windows and their positions, and the user confirmed that all
custom shortcuts worked. Earlier discovery/shortcut regressions are fixed.
See [EVIDENCE.md](EVIDENCE.md) for the distinction between automated and manual
evidence. Implementation
details and the source-to-runtime mapping are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Reproduce without changing your desktop

```sh
git clone https://github.com/tomasmark79/gnome-shell-restart-nix.git
cd gnome-shell-restart-nix

python3 -m unittest discover -s tests -p 'test_*.py'
nix develop .#rebind -c python3 tests/isolated.py \
  --reset-runtime --soak-seconds 65 --output artifacts/complete-context
nix develop .#type-rebind -c python3 tests/type-rebind-supervisor.py \
  tgnome-type-rebind-probe artifacts/native-control.json
nix build --no-link .#full-context-native-vm
```

The desktop test creates its own headless compositor, private buses and profile.
The VM test boots a separate NixOS guest. Building either never activates a
host system configuration. `result.json`, logs and PNG screenshots record the
desktop evidence. The native control also runs under Valgrind.
Nix with flakes is required; the native-backend VM test also requires usable
KVM on x86_64 Linux. Builds can be large because Shell and its private GJS are
patched from source. No prebuilt binary cache is supplied by this project.

## NixOS configuration candidate

Test in isolation first. Add this input to your NixOS flake and import
`shellRestart.nixosModules.default` into your existing system's module list:

```nix
inputs.shellRestart = {
  url = "github:tomasmark79/gnome-shell-restart-nix";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

Your nixpkgs must provide exactly the versions above; the repository's pinned
nixpkgs revision is in `flake.lock`. Following a different nixpkgs revision is
not a promise of compatibility. The module is disabled unless explicitly enabled:

```nix
services.gnome-shell-context-restart = {
  enable = true;
  allowNativeBackend = true; # Explicit experimental deployment opt-in
};
```

The module patches only the Shell's GJS dependency, installs the controller and
fixture extension, and selects the patched user service. It rejects mismatched
Shell/GJS versions. Building your NixOS configuration is separate from
activation. No activation or change to an existing session is performed here.

The default package accepts resets only in an isolated headless compositor or
the identity-checked VM fixture. `allowNativeBackend` selects a separate
candidate that also requires the service's explicit native-reset environment
flag. The native-backend candidate and its user command passed the VM test and
one updated hardware trial; extended daily use and arbitrary extensions remain
unverified. See [USAGE.md](USAGE.md) for activation and rollback boundaries.

In a newly started session using that candidate, enable the included extension
with `gnome-extensions enable restart-island@tgnome.local`. The user-invoked
command is `restart-gnome-shell`. It pins the running Shell's unique bus owner,
requests cooperative preparation, and waits for a new runtime epoch and an
actually finalized old context. It never kills or respawns Mutter.

## Scope and limitations

- Requires an idle unlocked responsive Shell, without active overview, modal
  dialogs or screencasting. It cannot repair a dead compositor or arbitrary
  blocked JavaScript.
- There is no fixed replacement count limit. Readiness and concurrent-operation
  checks remain active; automated coverage currently exercises five cycles.
- Lock arrival during replacement, arbitrary third-party extensions,
  accessibility, multi-monitor changes and screen recording need separate coverage.
- The included extension is a development fixture with test APIs, not a
  hardened minimal distribution extension.
- The published candidate should be tested in a VM before activation. The
  verified desktop test does not establish that all daily desktop integration
  works on real hardware.

The NixOS module was evaluated with GNOME enabled and the native-backend option
selected, and both package variants were built. The host version was checked
as 50.5. A module evaluation or package build does not activate a configuration.

The implementation reattaches compatible static GTypes, uses permanent native
vfunc/signal bridges, restores per-runtime moving-GC hooks and drains retired
Shell registrations. A process-owned accessibility listener avoids libatspi's
missing constructor destroy notification. Native child reaping outlives GJS.
Reset dispatch waits until Mutter's outer loop, and native Status does not
enter JavaScript. Source files retain their upstream license notices.

This workspace contains source, reproducible tests and generic Nix integration.
It contains no machine-specific NixOS configuration or private host settings.

## Continue the work

Contributions and independent reproductions are welcome. Start with
[CONTRIBUTING.md](CONTRIBUTING.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[EVIDENCE.md](EVIDENCE.md). Useful next steps include a smaller production
controller, longer stress runs, extension compatibility and upstream review of
the GJS lifetime changes. Do not treat a UI-only redraw as a complete restart.

Project contributions are licensed under GPL-2.0-or-later; upstream notices and
licenses remain applicable. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
