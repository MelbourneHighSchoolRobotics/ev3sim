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
  python = pkgs.python39.withPackages (p: with p; [ pip setuptools wheel ]);
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
    ${python.interpreter} -m pip download \
      --dest $out \
      --requirement $src \
      --only-binary ":all:" \ # Only get wheels, not source
      --platform ${platform} \
      --python-version ${pyVersion} \
      --implementation cp \ # Force CPython
      --abi "cp${pyVersion}" \
      -f ${ev3dev2} # Hack to find ev3dev2 wheel
  '';

  outputHashMode = "recursive";
  outputHashAlgo = "sha256";
  outputHash = sha256;
}