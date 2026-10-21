{ pkgs }:
assert pkgs.lib.assertMsg (pkgs.gnome-shell.version == "50.5") "This patch requires GNOME Shell 50.5";
assert pkgs.lib.assertMsg (pkgs.gjs.version == "1.88.1") "This patch requires GJS 1.88.1";
let
  uuid = "restart-island@tgnome.local";
  interruptGjs = pkgs.gjs.overrideAttrs (old: {
    pname = "tgnome-gjs";
    postPatch = (old.postPatch or "") + ''
      patch -p1 --fuzz=0 < ${./shell/gjs-interruption.patch}
    '';
  });
  nativeGjs = interruptGjs.overrideAttrs (old: {
    pname = "tgnome-native-type-gjs";
    postPatch = (old.postPatch or "") + ''
      cat ${./shell/gjsNativeType.cpp.inc} >> gjs/context.cpp
    '';
  });
  gjs = nativeGjs.overrideAttrs (old: {
    pname = "tgnome-type-rebind-gjs";
    nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ pkgs.python3 ];
    postPatch = (old.postPatch or "") + ''
      cp ${./shell/gjsTypeRebindPrivate.inc} gi/tgnomeTypeRebindPrivate.inc
      cp ${./shell/gjsTypeRebindVfunc.inc} gi/tgnomeTypeRebindVfunc.inc
      cp ${./shell/gjsCallbackLifetimes.inc} gi/tgnomeCallbackLifetimes.inc
      python3 ${./shell/buildTypeRebind.py}
    '';
  });
  panelShell = pkgs.gnome-shell.overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      patch -p1 --fuzz=0 < ${./shell/panel-lifecycle.patch}
      cat ${./shell/panelLifecycle.js} >> js/ui/panel.js
      cat ${./shell/mainLifecycle.js} >> js/ui/main.js
    '';
  });
  runtimeShell = panelShell.overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      patch -p1 --fuzz=0 < ${./shell/native-loop.patch}
      cp ${./shell/runtimeInit.js} js/ui/init.js
      cp ${./shell/tgnome-runtime.h} src/tgnome-runtime.h
      cat ${./shell/runtimeGlobal.c.inc} >> src/shell-global.c
      substituteInPlace js/misc/signalTracker.js js/ui/environment.js \
        js/ui/extensionSystem.js js/ui/layout.js js/ui/main.js \
        --replace-fail "'shutdown'" "'tgnome-ui-reset'"
    '';
  });
  shell = (runtimeShell.override { inherit gjs; }).overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      cat ${./shell/fullContextInit.js} ${./shell/runtimeInit.js} > js/ui/init.js
      cat ${./shell/fullContextAtspi.c.inc} >> src/shell-global.c
      cat ${./shell/fullContextState.c.inc} >> src/shell-global.c
      cat ${./shell/fullContextShellDBus.js} >> js/ui/shellDBus.js
      python3 ${./shell/buildFullContext.py}
    '';
  });
  # Explicit deployment candidate. The default shell remains fixture-only.
  nativeShell = shell.overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      substituteInPlace src/tgnome-runtime.h --replace-fail \
        '(headless || tgnome_security_vm)' \
        '(headless || tgnome_security_vm || g_strcmp0 (g_getenv ("TGNOME_ALLOW_NATIVE_CONTEXT_RESET"), "1") == 0)'
    '';
  });
  extension = pkgs.runCommand "tgnome-ui-island-0.1" {} ''
    mkdir -p $out/share/gnome-shell/extensions/${uuid}
    cp ${./extension}/* $out/share/gnome-shell/extensions/${uuid}/
  '';
  cli = pkgs.writeShellApplication {
    name = "tgnome";
    runtimeInputs = [ pkgs.python3 pkgs.glib ];
    text = ''exec python3 ${./tgnome.py} "$@"'';
  };
  restart = pkgs.writeShellApplication {
    name = "restart-gnome-shell";
    runtimeInputs = [ pkgs.python3 pkgs.glib ];
    text = ''
      export TGNOME_CLI_SOURCE=${./tgnome.py}
      exec python3 ${./restart.py} "$@"
    '';
  };
  probe = pkgs.stdenv.mkDerivation {
    pname = "tgnome-client-probe";
    version = "0.1";
    src = pkgs.lib.cleanSourceWith {
      src = ./tests;
      filter = path: type: type == "directory" || baseNameOf path == "probe.c";
    };
    nativeBuildInputs = [ pkgs.pkg-config ];
    buildInputs = [ pkgs.gtk3 pkgs.wayland pkgs.libx11 ];
    buildPhase = "cc -Wall -Wextra -Werror probe.c -o tgnome-client-probe $(pkg-config --cflags --libs gtk+-3.0 wayland-client x11)";
    installPhase = "mkdir -p $out/bin; cp tgnome-client-probe $out/bin/";
  };
  nativeProbe = pkgs.stdenv.mkDerivation {
    pname = "tgnome-type-rebind-probe";
    version = "0.1";
    src = ./tests/type-rebind-probe.cpp;
    dontUnpack = true;
    nativeBuildInputs = [ pkgs.pkg-config ];
    buildInputs = [ gjs pkgs.spidermonkey_140 ];
    buildPhase = ''
      $CXX -g -std=c++17 -Wall -Wextra -Werror -I${./tests} "$src" \
        -o tgnome-type-rebind-probe $(pkg-config --cflags --libs gjs-1.0 mozjs-140)
    '';
    installPhase = "mkdir -p $out/bin; cp tgnome-type-rebind-probe $out/bin/";
  };
in {
  inherit shell nativeShell gjs extension cli restart probe nativeProbe uuid;
}
