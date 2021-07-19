{ pkgs
, stdenv
, ...
}:
let
  version = pkgs.callPackage ./version.nix {};
  wine = pkgs.callPackage ./wine.nix {};
  fetchRequirements = pkgs.callPackage ./fetch-requirements.nix {};
  python64 = pkgs.callPackage ./python.nix {};
  python32 = pkgs.callPackage ./python.nix { is32bit = true; };
  nsis = pkgs.callPackage ./nsis.nix {};

  requirements = ./../requirements.txt;
  python64Deps = fetchRequirements {
    inherit requirements;
    is32bit = false;
    sha256 = "sha256-uixtPHJMs0Dxn+DgnxQ8NQJYkPmTadg0ZiXnUBjmCto=";
  };
  python32Deps = fetchRequirements {
    inherit requirements;
    is32bit = true;
    sha256 = "sha256-XqSAK1Uy2SxN4EL08xNmEEDccJUcivQDoQIEJ2dfi8w=";
  };
in
stdenv.mkDerivation {
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

    # Build and install the final binaries
    mkdir python_embed-64/wheels
    ${wine} python_embed-64/python.exe -m pip wheel \
      -w python_embed-64/wheels \
      -f ${python64Deps} --no-index \
      --no-build-isolation \
      .
    
    mkdir python_embed-32/wheels
    ${wine} python_embed-32/python.exe -m pip wheel \
      -w python_embed-32/wheels \
      -f ${python32Deps} --no-index \
      --no-build-isolation \
      .

    ${pkgs.python39.interpreter} build_exe.py
  '';

  installPhase = ''
    mkdir $out
    cp installer-{32,64}bit.exe $out
  '';
}