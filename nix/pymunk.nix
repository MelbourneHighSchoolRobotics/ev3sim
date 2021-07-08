{ lib
, buildPythonPackage
, fetchPypi
, cffi
, ...
}:

buildPythonPackage rec {
  pname = "pymunk";
  version = "6.0.0";

  propagatedBuildInputs = [ cffi ];

  src = fetchPypi {
    inherit version;
    pname = "pymunk";
    sha256 = "04jqqd2y0wzzkqppbl08vyzgbcpl5qj946w8da2ilypqdx7j2akp";
    extension = "zip";
  };
  doCheck = false;
}