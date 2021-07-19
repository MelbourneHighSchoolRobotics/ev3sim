# Fetch and cache Windows wheels for requirements
{ pkgs
, stdenv
, ...
}:

{ requirements
, is32bit ? false
, sha256 ? ""
}:
let
  version = pkgs.callPackage ./version.nix {};
  wine = pkgs.callPackage ./wine.nix {};
  python = pkgs.callPackage ./python.nix { inherit is32bit; };
  ev3dev2 = pkgs.callPackage ./ev3dev2-wheel.nix {};

  platform = if is32bit then "win32" else "win_amd64";
in
stdenv.mkDerivation {
  pname = "ev3sim-${platform}-requirements";
  inherit version;

  src = requirements;

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir $out
    ${wine} ${python}/python.exe -m pip wheel \
      --wheel-dir $out \
      --requirement $src \
      -f ${ev3dev2} # Hack to find ev3dev2 wheel
  '';

  outputHashMode = "recursive";
  outputHashAlgo = "sha256";
  outputHash = sha256;
}
