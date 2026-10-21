# Trying the native-backend candidate

This is an experimental modification of GNOME Shell and its private GJS build.
Save work and reproduce the isolated tests first. A separate terminal still
belongs to the graphical session and is not protection from a compositor crash.

## Build before activation

Import the flake module and enable the two options shown in the README. Keep
your existing NixOS configuration and boot generation available for rollback.
In the commands below, replace `HOST` with your flake's configuration name:

```sh
nix build --out-link result-shell-restart \
  .#nixosConfigurations.HOST.config.system.build.toplevel
sudo ./result-shell-restart/bin/switch-to-configuration dry-activate
```

The module prevents automatic restart/stop of the Shell and session manager
when their definitions change. Your display manager and other services are
controlled by your own NixOS configuration. Inspect the preview before activating:
a build cannot demonstrate that your current session will survive activation.

Record the current system outside the checkout. Temporarily activate the build
only when ready to close the current graphical session:

```sh
mkdir -p ~/.local/state/gnome-shell-restart
if [ ! -s ~/.local/state/gnome-shell-restart/previous-system ]; then
  readlink -f /run/current-system \
    > ~/.local/state/gnome-shell-restart/previous-system
fi
sudo ./result-shell-restart/bin/switch-to-configuration test
```

Log out normally and log in again. This initial logout closes applications;
an already-running Shell cannot acquire new native code. `test` activation does
not select a new default boot generation. Keep your previous boot entry.

## Perform the cooperative restart

```sh
gnome-extensions enable restart-island@tgnome.local
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/gnome/Shell/TgnomeRuntime \
  --method org.gnome.Shell.TgnomeRuntime.Status
```

An absent native endpoint means the matching patched session is not running.
Open a scratch document, type text and keep it open. Check application discovery
and your shortcuts before proceeding. Close overview, menus and modal dialogs;
leave the desktop unlocked and stop screen sharing/recording.

```sh
restart-gnome-shell
```

Success reports `wholeShellRestarted: true`, `compositorPreserved: true` and
different runtime epochs. Check the original document's text, type into it,
launch another application, try custom shortcuts, overview, panel menus and
lock/unlock. Observe the session for at least 65 seconds. A refused preparation
does not mean a reset occurred; close the reported active UI before retrying.
After a timeout, inspect Status and logs before another attempt.

Never substitute killing Mutter, `gnome-shell --replace` or restarting its
systemd service: those can disconnect clients.

## Return to the saved system

Reboot into the previous boot configuration, or restore the recorded system:

```sh
previous_system=$(cat ~/.local/state/gnome-shell-restart/previous-system)
sudo "$previous_system/bin/switch-to-configuration" test
```

If necessary, use Ctrl+Alt+F3 and log in on a text console. Restoration can
restart services. Save work and log out/back in or reboot to replace the running
patched process. Disable the module's `enable` option in subsequent builds to
stop including the patch. This project does not automatically activate or reboot.
