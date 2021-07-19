{
  description = "A simulator for soccer robots programmed with ev3dev.";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/21.05";
  # On unstable to use some new python packages. Eventually will be merged into Nix 21.11
  inputs.unstable.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  inputs.mindpile.url = "github:MelbourneHighSchoolRobotics/mindpile";
  inputs.mindpile.inputs.nixpkgs.follows = "nixpkgs";

  outputs = { self, nixpkgs, unstable, mindpile }: {
    packages.x86_64-linux =
      with import nixpkgs { system = "x86_64-linux"; };
      let
        unstablePkgs = import unstable { system = "x86_64-linux"; };
      in
      {
        pymunk = callPackage ./nix/pymunk.nix python39Packages;
        pygame-gui = callPackage ./nix/pygame-gui.nix python39Packages;

        linux =
          pkgs.python39Packages.buildPythonPackage (let
            version = callPackage ./nix/version.nix {};
          in {
            pname = "ev3sim";
            version = version;
            src = builtins.path { path = ./.; name = "ev3sim"; };
            propagatedBuildInputs = with pkgs.python39Packages; [
              numpy
              pygame
              pyyaml
              self.packages.x86_64-linux.pymunk
              unstablePkgs.python39Packages.ev3dev2
              unstablePkgs.python39Packages.opensimplex
              self.packages.x86_64-linux.pygame-gui
              mindpile.packages.x86_64-linux.mindpile
              sentry-sdk
              debugpy
              requests
            ];
            preBuild = ''
              # Remove version pinning (handled by Nix)
              sed -i -e 's/^\(.*\)[><=]=.*$/\1/g' requirements.txt
              # Remove Windows-only dependency
              substituteInPlace requirements.txt --replace "python-certifi-win32" ""
            '';
            doCheck = false;
          });
        
        windows = pkgs.callPackage ./nix/windows-installer.nix {};
      };

    defaultPackage.x86_64-linux = self.packages.x86_64-linux.linux;
  };
}
