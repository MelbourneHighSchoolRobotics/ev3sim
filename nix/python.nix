# Python embedded distribution for Windows with pip
{ pkgs, stdenv, fetchzip, is32bit ? false, ... }:
let
  wine = pkgs.callPackage ./wine.nix { };
  fetchWheel = pkgs.callPackage ./fetch-wheel.nix { };
  pip = fetchWheel {
    pname = "pip";
    version = "21.1.3";
    sha256 = "01520f9zj482ml1y2cnqxbzpldy59p402f2l8qr0gp7y243pdjvq";
  };
  setuptools = fetchWheel {
    pname = "setuptools";
    version = "57.2.0";
    sha256 = "03hrybnjma3pchin9g5k30fh5xxmsvb9xspmypj03frz2brl5fxl";
  };
  wheel = fetchWheel {
    pname = "wheel";
    version = "0.36.2";
    dist = "py2.py3";
    python = "py2.py3";
    sha256 = "03nw2n951cpladw5z0hfm4n1hjfxm9rl6chyr8k3qxp5y22v3dbq";
  };
in stdenv.mkDerivation rec {
  pname = "python-windows-embed${if is32bit then "32" else "64"}";
  version = "3.9.6";

  src = fetchzip (if is32bit then {
    url =
      "https://www.python.org/ftp/python/${version}/python-${version}-embed-win32.zip";
    sha256 = "CrLZ2UBfHvJk4zCBERCyO/hNpJ0torFKtSEv5jJKY48=";
    stripRoot = false;
  } else {
    url =
      "https://www.python.org/ftp/python/${version}/python-${version}-embed-amd64.zip";
    sha256 = "yAfSN0U5QScV4JVvb6FbcQyakppN2qniB3LmhPitPzY=";
    stripRoot = false;
  });

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir $out
    cp -r $src/* $out

    substituteInPlace $out/python39._pth --replace '#import site' 'import site'

    ${wine} $out/python.exe "${pip.wheel}/pip" install --no-index ${pip.wheel} ${setuptools.wheel} ${wheel.wheel}
  '';
}
