#! /usr/bin/env nix-shell
#! nix-shell -i bash -p nix-linter
SRC="$(dirname "$(dirname "$(readlink -fm "$0")")")"
nix-linter -r -v $SRC
