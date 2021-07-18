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
  winepath = "${winePkg}/bin/winepath";

  ev3dev2 = fetchFromGitHub {
    owner = "ev3dev";
    repo = "ev3dev-lang-python";
    rev = "2.1.0";
    sha256 = "XxsiQs3k5xKb+3RewARbvBbxaztdvdq3w5ZMgTq+kRc=";
    fetchSubmodules = true;
  };
in
stdenv.mkDerivation rec {
  pname = "ev3sim-windows-dependencies";
  inherit version;

  src = builtins.path { path = ./../requirements.txt; name = "requirements.txt"; };

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir $out
    export HOME=$TMPDIR
    ${wine} ${python-embed}/python.exe -m pip install $(${winepath} -w ${ev3dev2})
    ${wine} ${python-embed}/python.exe -m pip wheel -w $out -r $src
    # ${wine} ${python-embed}/python.exe -m pip download -d $out -r $src
  '';
}