# Runtime replacement and lifetime boundaries

Mutter, ShellGlobal, native display/input objects, Wayland sockets and existing
client surfaces retain their original process lifetime. The entire GjsContext,
SpiderMonkey context/runtime, Shell global, ESM module graph, Main and JavaScript
window manager are destroyed and bootstrapped again. A context weak-notify and
distinct runtime epochs measure this directly; a new UI generation alone is
not accepted as proof.

The native compositor loop is moved outside the old `init.js` evaluation by
`shell/native-loop.patch`. The controller prepares an idle unlocked desktop,
finishes the time-limits backend shutdown, releases Shell keybindings and
disables the fixture extension. The native supervisor then emits the Shell
shutdown signal, removes retired event registrations, releases the old context
and loads a new complete `init.js`.

Static GTypes cannot be unregistered with a context. `buildTypeRebind.py` and
the two `gjsTypeRebind*.inc` files therefore allow reattaching compatible native
metadata only after its former context has finalized. Parent, interface,
property and signal metadata must match. A live former owner or incompatible
schema is rejected. No per-generation GType names are allocated.

Native libffi dispatchers keep process-lifetime vtable addresses. The active
context supplies its own delegate; invalidation clears that delegate before
the old trampoline can be freed. Calls during the gap use the native parent
implementation or a neutral return. Default class-signal handlers use the same
native ownership principle. Ordinary per-context signal handlers detach.

The GJS patch also clears destroyed prototype qdata, registers the weak-wrapper
moving-GC hook for every new runtime, and reopens the empty native toggle queue.
The full Shell reproduced a wrapper-toggle crash without the latter changes;
recreating a standalone context alone did not reproduce that crash.

`fullContextInit.js` tracks JS-owned GLib sources, Mutter redraw callbacks and
idle watches. Native compositor work is outside the registry. IBus child exit
is reaped by native code after the JS runtime has gone. `fullContextAtspi.c.inc`
keeps one process-owned accessibility listener because libatspi 2.60 does not
invoke its constructor destroy notification. Replaceable ordinary signal
handlers deliver events to the current Shell without allocating an immortal
JS callback per restart.

The VM additionally reproduced reset during a nested GJS main loop: the native
Status query itself entered JS, and its nested dispatch attempted context
replacement before the original evaluation returned. Complete-context Status
now reads native data, and reset defers while `g_main_depth() > 1`. The corrected
VM passes overview input before and after replacement.

`gjsCallbackLifetimes.inc` provides native callback counts per runtime without
holding JS values or keeping contexts alive. Final verification requires empty
retired epochs, stable native type/dispatcher counts, actual old context
finalization, functional Shell input and the original clients' unchanged
connection identities. The standalone control also calls native vfuncs and
signals during the context gap and reaps children after context disposal.

Recovery remains cooperative and cannot safely interrupt arbitrary blocked
JavaScript. There is no fixed replacement count limit; idle/unlocked checks and
concurrent-operation guards remain active. The earlier UI-only fallback stays
in the research project and is not used as evidence of full runtime replacement.

External accelerator grabs belong to Mutter and survive runtime destruction.
`fullContextState.c.inc` keeps their action IDs, D-Bus sender names and allowed
action modes as native JSON, without retaining JavaScript objects.
`fullContextShellDBus.js` restores routing and sender watches in the new Shell.
Existing media-key services therefore keep working without restarting them.
`fullContextInit.js` also releases retired direct D-Bus signal subscriptions and
name watches. The retired callback ledger is empty after all five tested cycles.

The NixOS module explicitly removes generated service PATH overrides for Shell
and the session manager. Both inherit the login manager's PATH; otherwise Gio
filters applications whose TryExec executable is missing from that narrow PATH.
