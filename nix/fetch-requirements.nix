# Fetch and cache Windows wheels for requirements
{ lib
, pkgs
, stdenv
, fetchFromGitHub
, ...
}:

{ requirements
, pyVersion ? "39"
, is32bit ? false
, sha256 ? ""
}:
let
  version = pkgs.callPackage ./version.nix {};
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  python = pkgs.callPackage ./python.nix { inherit is32bit; };
  ev3dev2 = pkgs.callPackage ./ev3dev2-wheel.nix {};

  platform = if is32bit then "win32" else "win_amd64";
in
stdenv.mkDerivation rec {
  pname = "ev3sim-windows-dependencies";
  inherit version;

  src = requirements;

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir $out
    export WINEPREFIX=$TMPDIR/.wine
    ${wine} ${python}/python.exe -m pip wheel \
      --wheel-dir $out \
      --requirement $src \
      -f ${ev3dev2} # Hack to find ev3dev2 wheel
  '';

  outputHashMode = "recursive";
  outputHashAlgo = "sha256";
  outputHash = sha256;
}