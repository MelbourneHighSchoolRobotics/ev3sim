{ pkgs, mindpile, ... }:
pkgs.python39Packages.buildPythonPackage
(let version = pkgs.callPackage ./version.nix { };
in {
  pname = "ev3sim";
  inherit version;
  src = builtins.path {
    path = ./..;
    name = "ev3sim";
  };
  propagatedBuildInputs = with pkgs.python39Packages; [
    numpy
    pygame
    pyyaml
    pymunk
    ev3dev2
    opensimplex
    pygame-gui
    mindpile
    sentry-sdk
    debugpy
    requests
  ];
  preBuild = ''
    # Remove version pinning (handled by Nix)
    sed -i -e 's/^\(.*\)[><=]=.*$/\1/g' requirements.txt
    # Remove Windows-only dependency
    substituteInPlace requirements.txt --replace "python-certifi-win32" ""
  '';
  doCheck = false;
})
