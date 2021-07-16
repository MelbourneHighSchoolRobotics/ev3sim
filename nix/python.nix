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
  getPipSrc = fetchFromGitHub {
    owner = "pypa";
    repo = "get-pip";
    rev = "21.1.3";
    sha256 = "sha256-oAbZJZxCjL9kvBvN7KhJ1TC1iPUFJa+VYfes74q8dWU=";
  };
  getPip = "${getPipSrc}/public/get-pip.py";
in
stdenv.mkDerivation rec {
  pname = "python-windows-embed";
  version = "3.9.6";

  src = (if is32bit then fetchzip {
    url = "https://www.python.org/ftp/python/${version}/python-${version}-embed-win32.zip";
    sha256 = "CrLZ2UBfHvJk4zCBERCyO/hNpJ0torFKtSEv5jJKY48=";
    stripRoot = false;
  } else fetchzip {
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
    ${wine} $out/python.exe ${getPip}
  '';
}