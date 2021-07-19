# Based off https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/interpreters/python/fetchpypi.nix
{ pkgs, fetchurl }:
{ pname, version, dist ? "py3", python ? "py3", abi ? "none", platform ? "any", sha256 }:
let
  name = "${pname}-${version}-${python}-${abi}-${platform}.whl";
  url = "https://files.pythonhosted.org/packages/${dist}/${builtins.substring 0 1 pname}/${pname}/${name}";
  src = fetchurl {
    inherit url sha256;
  };
  path = pkgs.runCommandNoCC name {} ''
    mkdir $out
    cp ${src} $out/${name}
  '';
in {
  inherit name path;
  wheel = "${path}/${name}";
}
