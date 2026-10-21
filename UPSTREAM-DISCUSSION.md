# Draft for GNOME Discourse

Suggested destination: https://discourse.gnome.org/ — Desktop category, shell tag.
This is a prepared draft, not a posted message.

GNOME Shell's [contribution guidance](https://github.com/GNOME/gnome-shell#feature-requests)
recommends discussing major changes before opening a feature request or merge request.

---

## Experimental GJS runtime replacement under Wayland: reproducible study for feedback

Hi GNOME Shell and GJS developers,

I would like to share an experimental study of cooperatively replacing the
complete GNOME Shell JavaScript runtime while preserving the running Mutter
process and existing Wayland/XWayland clients. I am sharing it as reproducible
research for technical feedback, rather than proposing this patch collection
as ready for inclusion upstream.

Implementation and reproduction commands:
https://github.com/tomasmark79/gnome-shell-restart-nix

Research companion, including failed approaches and 224 sanitized historical
reports:
https://github.com/tomasmark79/gnome-shell-restart-research

The tested stack is GNOME Shell/Mutter 50.5, GJS 1.88.1 and SpiderMonkey 140 on
x86_64 NixOS, with pinned dependencies. The `gnome-shell` process is not replaced:
its GjsContext, JS runtime/global and Shell module graph are destroyed and
initialized again while Mutter continues running.

The isolated desktop and native-backend VM tests each complete five replacements.
They check old-context finalization, changed runtime epochs, the same compositor
PID, unchanged original client socket identity, retained unsaved text and
subsequent input into the original Wayland/XWayland clients. The VM additionally
tests custom shortcuts, overview, logind locking and actual GDM/PAM authentication,
including rejection of an incorrect password. A 65-second observation and native
retired-callback accounting are included. Two VM replacements use Alt+F2, `r`,
Enter through the same guarded controller.

A separate manual hardware trial preserved seven windows and their positions;
the user confirmed working personal shortcuts. That hardware observation does
not independently establish the socket/input checks performed in isolation.

The implementation experiments with compatible static GType reattachment,
process-lifetime native vfunc bridges and cleanup of per-runtime registrations.
It also preserves external accelerator routing across replacement. The native
main loop outlives GJS. The research repository records earlier realm,
interruption and UI-only reconstruction approaches and their limitations.

Important limits: this needs a responsive, idle, unlocked Shell and cannot
recover a dead Mutter or arbitrary blocked JavaScript. Broad extension,
accessibility and display-change compatibility, long stress runs and other
upstream versions remain unverified. The research archive is one source
snapshot, not an exact source history for every saved run.

The work was developed with substantial AI assistance. Passing these tests is
not a substitute for independent review of native ownership and lifetime safety.

Would this be useful research for Shell/GJS maintainers? In particular, I would
welcome feedback on whether static GType reattachment and native callback/vfunc
lifetime boundaries are a reasonable direction to investigate, or whether a
different architecture would be preferable. Which small, independently
reviewable experiment or negative control would be most useful next?
