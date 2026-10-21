# Contributing

The goal is complete GNOME Shell runtime replacement while Mutter and existing
Wayland/XWayland clients retain their identity and remain usable. A rebuilt
panel, new UI generation or successful D-Bus command alone is insufficient.

Use English for documentation, issues and pull requests. Keep changes focused;
explain the failure, resulting behavior and exact validation. Do not experiment
on someone else's active desktop. Use the private compositor and NixOS VM.

## Reproduce the baseline

The README lists the desktop, native/Valgrind and native-backend VM commands.
Use the pinned flake lock. VM tests need x86_64 Linux and KVM access; they may
take substantial time and disk space. A negative-control VM intentionally fails
and is documented in EVIDENCE.md; it is not part of the passing baseline.

Quick checks, also run by CI:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall -q tgnome.py restart.py shell tests
git diff --check
```

Quick CI checks do not establish desktop recovery. For changes to native/GJS
lifetimes, reset preparation, shortcut restoration or cleanup, rerun the
relevant end-to-end tests. Require changed epochs, actual context finalization,
the same compositor PID, original socket identity, post-recovery client input,
functional Shell controls, empty retired callback ledgers and repeatability.

Use `tests/verify-results.py` with the three generated evidence reports to
validate and fingerprint results. Store personal logs locally under ignored
`artifacts/`. Review screenshots, window titles, paths and environment data
before attaching them to public issues.

## Where to start

- Reduce the fixture extension and test-only APIs to a minimal user controller.
- Stress many more than five consecutive replacements and inspect memory growth.
- Exercise extension compatibility, accessibility and display hotplug.
- Test lock/screen-sharing races and fail-closed preparation behavior.
- Review GType reattachment and native callback ownership with GJS maintainers.
- Port to other exact upstream versions with fresh reproducible evidence.

There is no claim of a general solution for a hung JS callback or dead Mutter.
Do not weaken preparation/admission guards to make a test pass.

## Reports and licensing

Include exact GNOME/GJS versions, nixpkgs and project revisions, test command,
whether the failure was isolated or live, and a small redacted log excerpt.
Distinguish observed results from hypotheses and builds from activation.

Contributions must be compatible with the project license and preserve upstream
notices. This project is independent of GNOME and currently experimental.
