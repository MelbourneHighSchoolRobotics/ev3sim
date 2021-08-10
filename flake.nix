{
  description = "A simulator for soccer robots programmed with ev3dev.";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/21.05";
  # On unstable to use some new python packages. Eventually will be merged into Nix 21.11
  inputs.unstable.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.mindpile.url = "github:MelbourneHighSchoolRobotics/mindpile";
  inputs.mindpile.inputs.nixpkgs.follows = "nixpkgs";
  inputs.mindpile.inputs.flake-utils.follows = "flake-utils";

  outputs = { nixpkgs, unstable, flake-utils, mindpile, ... }:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        unstablePkgs = unstable.legacyPackages.${system};
      in rec {
        packages = {
          linux = pkgs.callPackage ./nix/linux.nix {
            inherit (unstablePkgs.python39Packages) ev3dev2 opensimplex pymunk pygame pygame-gui;
            mindpile = mindpile.legacyPackages.${system}.mindpile;
          };

          windows = pkgs.callPackage ./nix/windows-installer.nix { };
        };
        defaultPackage = packages.linux;
      });
}
