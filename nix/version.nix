{ lib }:
let
  versionFile = builtins.readFile ./../ev3sim/__init__.py;
  versionLine = lib.findFirst (lib.hasPrefix "__version__") "" (lib.splitString "\n" versionFile);
  version = lib.removePrefix "__version__ = \"" (lib.removeSuffix "\"" versionLine);
in
  version