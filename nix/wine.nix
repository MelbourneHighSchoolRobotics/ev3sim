{ pkgs, ... }:
let
  wine = pkgs.wineWowPackages.minimal;
  wrapper = pkgs.writeShellScript "wine" ''
    export WINEPREFIX=$TMPDIR/.wine
    # Supress unhelpful warnings
    export WINEDEBUG=-all
    # Disable looking for Gecko support
    export WINEDLLOVERRIDES="mscoree,mshtml="

    ${wine}/bin/wine64 "$@"
  '';
in wrapper
