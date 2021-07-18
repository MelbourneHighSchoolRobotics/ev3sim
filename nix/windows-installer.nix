{ lib
, pkgs
, stdenv
, ...
}:
let
  version = pkgs.callPackage ./version.nix {};
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  python64 = pkgs.callPackage ./python.nix {};
  python64Deps = pkgs.callPackage ./windows-dependencies.nix { python-embed = python64; };
  python32 = pkgs.callPackage ./python.nix { is32bit = true; };
  python32Deps = pkgs.callPackage ./windows-dependencies.nix { python-embed = python32; };
  nsis = pkgs.callPackage ./nsis.nix {};
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

    export HOME=$TMPDIR

    mkdir python_embed-64/wheels
    cp ${python64Deps}/* python_embed-64/wheels
    ${wine} python_embed-64/python.exe -m pip wheel --no-index --no-deps --no-build-isolation -w python_embed-64/wheels .
    
    mkdir python_embed-32/wheels
    cp ${python32Deps}/* python_embed-32/wheels
    ${wine} python_embed-32/python.exe -m pip wheel --no-index --no-deps --no-build-isolation -w python_embed-32/wheels .

    ${pkgs.python39.interpreter} build_exe.py
  '';

  installPhase = ''
    mkdir $out
    cp -r installer-{32,64}bit.exe python_embed-{32,64} $out
  '';
}