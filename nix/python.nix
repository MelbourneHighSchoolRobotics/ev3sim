{ lib
, pkgs
, stdenv
, fetchurl
, fetchzip
, fetchFromGitHub
, is32bit ? false
, ...
}:
let
  winePkg = pkgs.callPackage ./wine.nix {};
  wine = "${winePkg}/bin/wine64";
  winepath = "${winePkg}/bin/winepath";
  pipWheelName = "pip-21.1.3-py3-none-any.whl";
  pipWheelSrc = fetchurl {
    url = "https://files.pythonhosted.org/packages/47/ca/f0d790b6e18b3a6f3bd5e80c2ee4edbb5807286c21cdd0862ca933f751dd/${pipWheelName}";
    sha256 = "01520f9zj482ml1y2cnqxbzpldy59p402f2l8qr0gp7y243pdjvq";
  };
  pipWheel = pkgs.runCommandNoCC "pip-wheel" {} ''
    mkdir $out
    cp ${pipWheelSrc} $out/${pipWheelName}
  '';
in
stdenv.mkDerivation rec {
  pname = "python-windows-embed";
  version = "3.9.6";

  src = fetchzip (if is32bit then {
    url = "https://www.python.org/ftp/python/${version}/python-${version}-embed-win32.zip";
    sha256 = "CrLZ2UBfHvJk4zCBERCyO/hNpJ0torFKtSEv5jJKY48=";
    stripRoot = false;
  } else {
    url = "https://www.python.org/ftp/python/${version}/python-${version}-embed-amd64.zip";
    sha256 = "yAfSN0U5QScV4JVvb6FbcQyakppN2qniB3LmhPitPzY=";
    stripRoot = false;
  });

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir $out
    cp -r $src/* $out

    substituteInPlace $out/python39._pth --replace '#import site' 'import site'
    
    export HOME=$TMPDIR
    export PIP=$(${winepath} -w ${pipWheel}/${pipWheelName})
    ${wine} $out/python.exe "$PIP\pip" install --no-index $PIP
    ${wine} $out/python.exe -m pip install setuptools
  '';
}