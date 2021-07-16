{
  description = "A simulator for soccer robots programmed with ev3dev.";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/21.05";
  inputs.mindpile.url = "github:MelbourneHighSchoolRobotics/mindpile";
  inputs.mindpile.inputs.nixpkgs.follows = "nixpkgs";

  outputs = { self, nixpkgs, mindpile }: {

    overlay = final: prev: {
      python39Packages = prev.python39Packages // {
        
      };
    };

    packages.x86_64-linux =
      with import nixpkgs { system = "x86_64-linux"; };
      {
        pymunk = callPackage ./nix/pymunk.nix python39Packages;
        ev3dev2 = callPackage ./nix/ev3dev2.nix python39Packages;
        opensimplex = callPackage ./nix/opensimplex.nix python39Packages;
        luddite = callPackage ./nix/luddite.nix python39Packages;
        pygame-gui = callPackage ./nix/pygame-gui.nix python39Packages;

        ev3sim =
          pkgs.python39Packages.buildPythonPackage (let
            versionFile = builtins.readFile ./ev3sim/__init__.py;
            versionLine = lib.findFirst (lib.hasPrefix "__version__") "" (lib.splitString "\n" versionFile);
            version = lib.removePrefix "__version__ = \"" (lib.removeSuffix "\"" versionLine);
          in {
            pname = "ev3sim";
            version = version;
            src = builtins.path { path = ./.; name = "ev3sim"; };
            propagatedBuildInputs = with pkgs.python39Packages; [
              numpy
              pygame
              pyyaml
              self.packages.x86_64-linux.pymunk
              self.packages.x86_64-linux.ev3dev2
              self.packages.x86_64-linux.opensimplex
              self.packages.x86_64-linux.luddite
              self.packages.x86_64-linux.pygame-gui
              mindpile.packages.x86_64-linux.mindpile
              sentry-sdk
              debugpy
              requests
            ];
            preBuild = ''
              substituteInPlace requirements.txt --replace "numpy==1.19.3" "numpy"
              substituteInPlace requirements.txt --replace "python-certifi-win32>=1.6" ""
            '';
            doCheck = false;
          });
        
        ev3sim-windows-installer = pkgs.callPackage ./nix/windows-installer.nix {};
      };

    defaultPackage.x86_64-linux = self.packages.x86_64-linux.ev3sim;
  };
}
