// This registry belongs to one complete GJS runtime. Track only registrations
// made through its JS wrappers; native Mutter watches and redraw work survive.
import TgnomeMeta from 'gi://Meta';

const tgnomeNativeWork = new Map();
function tgnomeTrackNativeWork(prototype, addName, removeName, completion) {
    const add = prototype[addName];
    const remove = prototype[removeName];
    prototype[addName] = function (...args) {
        const owner = this;
        if (!tgnomeNativeWork.has(owner))
            tgnomeNativeWork.set(owner, new Map());
        const work = tgnomeNativeWork.get(owner);
        const callbackIndex = args.length - 1;
        const callback = args[callbackIndex];
        let id = 0;
        args[callbackIndex] = function (...parameters) {
            const keep = callback.apply(this, parameters);
            if (completion === 'once' || (completion === 'boolean' && !keep))
                work.delete(id);
            return keep;
        };
        id = add.apply(owner, args);
        work.set(id, () => remove.call(owner, id));
        return id;
    };
    prototype[removeName] = function (id) {
        tgnomeNativeWork.get(this)?.delete(id);
        return remove.call(this, id);
    };
}
tgnomeTrackNativeWork(TgnomeMeta.Laters.prototype, 'add', 'remove', 'boolean');
tgnomeTrackNativeWork(TgnomeMeta.IdleMonitor.prototype, 'add_idle_watch', 'remove_watch');
tgnomeTrackNativeWork(TgnomeMeta.IdleMonitor.prototype, 'add_user_active_watch', 'remove_watch', 'once');

const tgnomeSignalSubscriptions = new Map();
const tgnomeSubscribe = Gio.DBusConnection.prototype.signal_subscribe;
const tgnomeUnsubscribe = Gio.DBusConnection.prototype.signal_unsubscribe;
Gio.DBusConnection.prototype.signal_subscribe = function (...args) {
    const id = tgnomeSubscribe.apply(this, args);
    if (!tgnomeSignalSubscriptions.has(this))
        tgnomeSignalSubscriptions.set(this, new Set());
    tgnomeSignalSubscriptions.get(this).add(id);
    return id;
};
Gio.DBusConnection.prototype.signal_unsubscribe = function (id) {
    tgnomeSignalSubscriptions.get(this)?.delete(id);
    return tgnomeUnsubscribe.call(this, id);
};
const tgnomeNameWatches = new Set();
const tgnomeUnwatchName = Gio.bus_unwatch_name;
for (const name of ['bus_watch_name', 'bus_watch_name_on_connection']) {
    const watch = Gio[name];
    if (typeof watch !== 'function')
        continue;
    Gio[name] = function (...args) {
        const id = watch.apply(Gio, args);
        tgnomeNameWatches.add(id);
        return id;
    };
}
Gio.bus_unwatch_name = function (id) {
    tgnomeNameWatches.delete(id);
    return tgnomeUnwatchName.call(Gio, id);
};

function tgnomeReleaseNativeWork() {
    for (const [connection, ids] of tgnomeSignalSubscriptions) {
        for (const id of ids)
            tgnomeUnsubscribe.call(connection, id);
    }
    tgnomeSignalSubscriptions.clear();
    for (const id of tgnomeNameWatches)
        tgnomeUnwatchName.call(Gio, id);
    tgnomeNameWatches.clear();
    for (const tracker of global._tgnomeFocusTrackers ?? []) {
        tracker.deregisterFocusListener();
        tracker.deregisterCaretListener();
        tracker._atspiListener.disconnect(tracker._tgnomeListenerSignal);
        tracker._atspiListener = null;
    }
    global._tgnomeFocusTrackers?.clear();
    let count = 0;
    for (const work of tgnomeNativeWork.values()) {
        for (const remove of work.values()) {
            remove();
            count++;
        }
        work.clear();
    }
    tgnomeNativeWork.clear();
    console.info(`TGNOME removed ${count} remaining JS Mutter registrations`);
    System.gc();
}
