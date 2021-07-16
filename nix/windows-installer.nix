{ lib
, pkgs
, stdenv
, ...
}:
let
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  python64 = pkgs.callPackage ./python.nix {};
  python32 = pkgs.callPackage ./python.nix { is32bit = true; };
  nsis = pkgs.callPackage ./nsis.nix {};
in
stdenv.mkDerivation rec {
  pname = "ev3sim-windows-installer";
  version = "0.0.2";

  src = builtins.path { path = ./..; name = "ev3sim"; };

  phases = [ "buildPhase" "installPhase" ];

  nativeBuildInputs = [ nsis ];

  buildPhase = ''
    cp -r ${python64} python_embed-64
    cp -r ${python32} python_embed-32
    
    cp -r $src/* .
    chmod a+w -R .
    ${pkgs.python39.interpreter} build_exe.py
  '';

  installPhase = ''
    mkdir $out
    cp installer-{32,64}bit.exe $out
  '';
}