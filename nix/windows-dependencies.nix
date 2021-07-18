# Fetch and cache Windows wheels for dependencies
# HACK! This accesses the internet and requires Nix sandboxing turned off
{ lib
, pkgs
, stdenv
, fetchFromGitHub
, python-embed ? pkgs.callPackage ./python.nix {}
, ...
}:
let
  version = pkgs.callPackage ./version.nix {};
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  ev3dev2 = pkgs.callPackage ./ev3dev2-wheel.nix {};
in
stdenv.mkDerivation rec {
  pname = "ev3sim-windows-dependencies";
  inherit version;

  src = builtins.path { path = ./../requirements.txt; name = "requirements.txt"; };

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir $out
    export HOME=$TMPDIR
    ${wine} ${python-embed}/python.exe -m pip wheel -w $out -f ${ev3dev2} -r $src
  '';
}