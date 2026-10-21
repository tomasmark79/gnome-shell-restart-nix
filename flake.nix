{
  description = "Experimental complete GNOME Shell 50.5 context restart with Mutter and clients retained";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/8ce73368d1efd4d657e9064d29b144a52046b4e8";
  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
    suite = import ./packages.nix { inherit pkgs; };
    testPython = pkgs.python3.withPackages (ps: [ ps.python-dbusmock ps.pygobject3 ]);
  in {
    overlays.default = final: prev: {
      gnome-shell = (import ./packages.nix { pkgs = prev; }).shell;
    };
    overlays.native-backend = final: prev: {
      gnome-shell = (import ./packages.nix { pkgs = prev; }).nativeShell;
    };
    nixosModules.default = import ./module.nix { inherit self; };
    packages.${system} = {
      default = suite.shell;
      shell = suite.shell;
      native-shell = suite.nativeShell;
      inherit (suite) gjs extension cli restart probe;
      type-rebind-probe = suite.nativeProbe;
      full-context-shortcuts-negative-vm = import ./tests/vm-security.nix {
        inherit pkgs;
        inherit (suite) probe extension;
        recoveryCli = pkgs.symlinkJoin {
          name = "gnome-shell-restart-tools";
          paths = [ suite.cli suite.restart ];
        };
        shell = suite.nativeShell.overrideAttrs (old: {
          postPatch = (old.postPatch or "") + ''
            substituteInPlace js/ui/shellDBus.js --replace-fail \
              '        tgnomeRestoreExternalAccelerators(this);' \
              '        this._tgnomeExternalModes = new Map();'
          '';
        });
        patched = true;
        fullContext = true;
        nativeBackend = true;
      };
      full-context-native-vm = import ./tests/vm-security.nix {
        inherit pkgs;
        inherit (suite) probe extension;
        recoveryCli = pkgs.symlinkJoin {
          name = "gnome-shell-restart-tools";
          paths = [ suite.cli suite.restart ];
        };
        shell = suite.nativeShell;
        patched = true;
        fullContext = true;
        nativeBackend = true;
      };
      full-context-vm = import ./tests/vm-security.nix {
        inherit pkgs;
        inherit (suite) probe extension;
        recoveryCli = suite.cli;
        shell = suite.shell.overrideAttrs (old: {
          NIX_CFLAGS_COMPILE = (old.NIX_CFLAGS_COMPILE or "") + " -DTGNOME_SECURITY_VM=1";
        });
        patched = true;
        fullContext = true;
      };
    };
    devShells.${system} = {
      rebind = pkgs.mkShell {
        packages = [ testPython pkgs.glib pkgs.dbus pkgs.gdb suite.shell
          pkgs.gsettings-desktop-schemas pkgs.mesa pkgs.xwayland suite.probe ];
        TGNOME_EXTENSION = "${suite.extension}/share/gnome-shell/extensions/${suite.uuid}";
        TGNOME_PROBE = "${suite.probe}/bin/tgnome-client-probe";
        TGNOME_SHELL = "${suite.shell}/bin/gnome-shell";
        TGNOME_ALLOW_PANEL_RELOAD = "1";
        TGNOME_ALLOW_RUNTIME_RESET = "1";
        TGNOME_REBIND_TYPES = "1";
      };
      type-rebind = pkgs.mkShell {
        packages = [ pkgs.python3 pkgs.gdb pkgs.valgrind suite.nativeProbe ];
      };
    };
  };
}
