{ lib
, buildPythonPackage
, fetchPypi
, ...
}:

buildPythonPackage rec {
  pname = "opensimplex";
  version = "0.3";

  src = fetchPypi {
    inherit version pname;
    sha256 = "0hd6kmxazwx20rygx0jx023rfvwlykbgfvii7kz9rfwxdmn8kf2r";
  };
  doCheck = false;
}