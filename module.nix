{ self }:
{ config, lib, pkgs, ... }:
let cfg = config.services.gnome-shell-context-restart;
in {
  options.services.gnome-shell-context-restart = {
    enable = lib.mkEnableOption "the experimental GNOME Shell 50.5 context restart patch";
    allowNativeBackend = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Explicitly permit cooperative context replacement in native Wayland sessions. Experimental; requires separate activation and a new session.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [{
      assertion = config.services.desktopManager.gnome.enable;
      message = "GNOME Shell context restart requires the GNOME desktop manager.";
    }];
    nixpkgs.overlays = [ (if cfg.allowNativeBackend then self.overlays.native-backend else self.overlays.default) ];
    environment.systemPackages = [
      self.packages.${pkgs.stdenv.hostPlatform.system}.cli
      self.packages.${pkgs.stdenv.hostPlatform.system}.restart
      self.packages.${pkgs.stdenv.hostPlatform.system}.extension
    ];
    systemd.user.services."gnome-session-manager@" = {
      restartIfChanged = false;
      stopIfChanged = false;
      environment.PATH = lib.mkForce null;
    };
    systemd.user.services."org.gnome.Shell@" = {
      restartIfChanged = false;
      stopIfChanged = false;
      serviceConfig.ExecStart = [ "" "${pkgs.gnome-shell}/bin/gnome-shell --mode=%i" ];
      environment = {
        # Inherit the login session PATH instead of NixOS's service-only PATH.
        PATH = lib.mkForce null;
        TGNOME_REBIND_TYPES = "1";
        TGNOME_ALLOW_RUNTIME_RESET = "1";
        TGNOME_TEST_FAILURES = "1";
      } // lib.optionalAttrs cfg.allowNativeBackend {
        TGNOME_ALLOW_NATIVE_CONTEXT_RESET = "1";
      };
    };
  };
}
