{ lib
, buildPythonPackage
, fetchPypi
, pillow
, ...
}:

buildPythonPackage rec {
  pname = "ev3dev2";
  version = "2.1.0.post1";

  propagatedBuildInputs = [ pillow ];

  src = fetchPypi {
    inherit version;
    pname = "python-ev3dev2";
    sha256 = "0cfd69b0e8b6ae2ac8f300d7faea602032d961cc526417554d7da35cd9730949";
  };
  doCheck = false;
}