{ lib
, pkgs
, stdenv
, ...
}:
let
  version = pkgs.callPackage ./version.nix {};
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  fetchRequirements = pkgs.callPackage ./fetch-requirements.nix {};
  python64 = pkgs.callPackage ./python.nix {};
  python32 = pkgs.callPackage ./python.nix { is32bit = true; };
  nsis = pkgs.callPackage ./nsis.nix {};

  requirements = builtins.path { path = ./../requirements.txt; name = "requirements.txt"; };
  python64Deps = fetchRequirements {
    inherit requirements;
    pyVersion = "39";
    is32bit = false;
    sha256 = "sha256-eh/dDjvnzGiyGwWhEztwIAwFgXwtgRluBChEiXgKpWY=";
  };
  python32Deps = fetchRequirements {
    inherit requirements;
    pyVersion = "39";
    is32bit = true;
    sha256 = "sha256-gFubpvxhl1w2GbkG52jtmJWiZDESd0wMR9/C/Yfod7g=";
  };
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

    export WINEPREFIX=$TMPDIR/.wine

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