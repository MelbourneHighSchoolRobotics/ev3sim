# NSIS with ExecDos plugin
{ pkgs, fetchzip, ... }:
let
  execDos = fetchzip {
    url = "https://nsis.sourceforge.io/mediawiki/images/0/0f/ExecDos.zip";
    sha256 = "mVo9/Gn7CAMUqF2P/wP10uCqw42GSTFxD2lwdx4aMUI=";
    stripRoot = false;
  };
in
pkgs.nsis.overrideAttrs (_: {
  postBuild = ''
    cp -r ${execDos}/* $out/share/nsis
  '';
})
