
// MediaKeys and other external clients keep their existing native grab IDs.
// Rebuild the routing and WM action modes around those IDs in every new Shell.
function tgnomeRestoreExternalAccelerators(service) {
    service._tgnomeExternalModes = new Map();
    const records = JSON.parse(global.tgnome_get_external_accelerators());
    for (const [action, sender, mode] of records) {
        service._grabbedAccelerators.set(action, sender);
        service._tgnomeExternalModes.set(action, mode);
        Main.wm.allowKeybinding(Meta.external_binding_name_for_action(action), mode);
        if (!service._grabbers.has(sender)) {
            const id = Gio.bus_watch_name(Gio.BusType.SESSION, sender, 0,
                null, service._onGrabberBusNameVanished.bind(service));
            service._grabbers.set(sender, id);
        }
    }
    console.info(`TGNOME restored ${records.length} external shortcut registrations`);
}

function tgnomePersistExternalAccelerators(service) {
    const records = [...service._grabbedAccelerators].map(([action, sender]) =>
        [action, sender, service._tgnomeExternalModes.get(action)]);
    global.tgnome_set_external_accelerators(JSON.stringify(records));
}

const tgnomeOriginalGrab = GnomeShell.prototype._grabAcceleratorForSender;
GnomeShell.prototype._grabAcceleratorForSender = function (accelerator, mode, flags, sender) {
    const action = tgnomeOriginalGrab.call(this, accelerator, mode, flags, sender);
    if (action !== Meta.KeyBindingAction.NONE) {
        this._tgnomeExternalModes.set(action, mode);
        tgnomePersistExternalAccelerators(this);
    }
    return action;
};

const tgnomeOriginalUngrab = GnomeShell.prototype._ungrabAccelerator;
GnomeShell.prototype._ungrabAccelerator = function (action) {
    const result = tgnomeOriginalUngrab.call(this, action);
    if (result) {
        this._tgnomeExternalModes.delete(action);
        tgnomePersistExternalAccelerators(this);
    }
    return result;
};
