{ buildPythonPackage, fetchPypi, pygame, ... }:

buildPythonPackage rec {
  pname = "pygame-gui";
  version = "0.5.7";

  propagatedBuildInputs = [ pygame ];

  src = fetchPypi {
    inherit version;
    pname = "pygame_gui";
    sha256 = "0nhlq6w0apwjxiggxqwsnivqpi6qsks3pxd1amww707hqg2wd6d6";
  };
  doCheck = false;
}
