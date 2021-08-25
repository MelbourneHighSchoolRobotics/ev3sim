{
  description = "A simulator for soccer robots programmed with ev3dev";

  # On unstable to use some new python packages. Eventually will be merged into Nix 21.11
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.mindpile.url = "github:MelbourneHighSchoolRobotics/mindpile";
  inputs.mindpile.inputs.nixpkgs.follows = "nixpkgs";
  inputs.mindpile.inputs.flake-utils.follows = "flake-utils";

  outputs = { nixpkgs, flake-utils, mindpile, ... }:
    flake-utils.lib.eachSystem [ "x86_64-linux" "x86_64-darwin" ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        mp = mindpile.legacyPackages.${system};
      in rec {
        packages = {
          unix = pkgs.callPackage ./nix/unix.nix {
            inherit (mp) mindpile;
          };

          windows = pkgs.callPackage ./nix/windows-installer.nix { };
        };
        defaultPackage = packages.unix;
      });
}
