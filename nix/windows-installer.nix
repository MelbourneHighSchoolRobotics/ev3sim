{ lib
, pkgs
, stdenv
, ...
}:
let
  version = pkgs.callPackage ./version.nix {};
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  winepath = "${winePkg}/bin/winepath";
  python64 = pkgs.callPackage ./python.nix {};
  python64Deps = pkgs.callPackage ./windows-dependencies.nix { python-embed = python64; };
  python32 = pkgs.callPackage ./python.nix { is32bit = true; };
  python32Deps = pkgs.callPackage ./windows-dependencies.nix { python-embed = python32; };
  nsis = pkgs.callPackage ./nsis.nix {};
  ev3dev2 = pkgs.callPackage ./ev3dev2-wheel.nix {};
in
stdenv.mkDerivation rec {
  pname = "ev3sim-windows-installer";
  inherit version;

  src = builtins.path { path = ./..; name = "ev3sim"; };

  phases = [ "buildPhase" "installPhase" ];

  nativeBuildInputs = [ nsis ];

  buildPhase = ''
    cp -r ${python64} python_embed-64
    cp -r ${python32} python_embed-32

    cp -r $src/* .
    chmod a+w -R .

    cp ev3sim/presets/default_config.yaml ev3sim/user_config.yaml

    mkdir python_embed-64/wheels
    mkdir python_embed-32/wheels
    export HOME=$TMPDIR
    ${wine} python_embed-64/python.exe -m pip wheel -w python_embed-64/wheels -f ${ev3dev2} .
    ${wine} python_embed-32/python.exe -m pip wheel -w python_embed-32/wheels -f ${ev3dev2} .

    ${pkgs.python39.interpreter} build_exe.py
  '';

  installPhase = ''
    mkdir $out
    cp -r installer-{32,64}bit.exe python_embed-{32,64} $out
  '';
}