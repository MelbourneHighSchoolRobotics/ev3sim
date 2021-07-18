# HACK! Build an ev3dev2 wheel natively as it doesn't build under Wine for some reason, and isn't on PyPi
{ pkgs, fetchurl, ... }:
let
  ev3dev2 = fetchurl {
    url = "https://files.pythonhosted.org/packages/8a/8c/2ddffc70572989acb5d2f60e5e1d7e93f6daf9b05200ac0e80d030e98950/python-ev3dev2-2.1.0.post1.tar.gz";
    sha256 = "0j89fgcmr8vx9maifr2jrihxjci0c3mgmmq0yg42mbmnx2q6kz8c";
  };
  python = pkgs.python39.withPackages (p: with p; [ pip setuptools wheel ]);
in
pkgs.runCommandNoCC "ev3dev2-wheel" {} ''
  mkdir $out
  ${python}/bin/python -m pip wheel -w $out --no-deps --no-index ${ev3dev2}
''
