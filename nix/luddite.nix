{ lib
, buildPythonPackage
, fetchPypi
, ...
}:

buildPythonPackage rec {
  pname = "luddite";
  version = "1.0.1";

  src = builtins.fetchurl {
    url = "https://github.com/jumptrading/luddite/archive/refs/tags/v1.0.1.tar.gz";
    sha256 = "1xbwz2xqpfafhhg9j59pmc0a7rq3dqf96vwbm7cfb7k4g0i9y2bd";
  };
  doCheck = false;
}