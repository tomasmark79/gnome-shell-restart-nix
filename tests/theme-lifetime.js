// Busless native St.Theme ownership regression. Does not create a display.
const {Gio, GLib, St} = imports.gi;
const directory = GLib.dir_make_tmp('tgnome-theme-control-XXXXXX');
const path = `${directory}/fixture.css`;
try {
    GLib.file_set_contents(path, '.tgnome-fixture { color: red; }');
    const file = Gio.File.new_for_path(path);
    const theme = new St.Theme();
    for (let cycle = 0; cycle < 20; cycle++) {
        theme.load_stylesheet(file);
        theme.load_stylesheet(file);
        const loaded = theme.get_custom_stylesheets();
        theme.unload_stylesheet(file);
        const unloaded = theme.get_custom_stylesheets();
        // Main.loadTheme() copies this list into a new St.Theme after reset.
        const next = new St.Theme();
        for (const entry of unloaded)
            next.load_stylesheet(entry);
        if (loaded.length !== 1 || loaded.some(item => !item) || unloaded.length)
            throw new Error(`Invalid stylesheet lifecycle: ${loaded.length}/${unloaded.length}`);
    }
    print(JSON.stringify({passed: true, cycles: 20, duplicateLoadIsIdempotent: true,
        noStaleStylesheetsAfterUnload: true}));
} finally {
    GLib.unlink(path);
    GLib.rmdir(directory);
}
