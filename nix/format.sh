#! /usr/bin/env nix-shell
#! nix-shell -i bash -p nixfmt
SRC="$(dirname "$(dirname "$(readlink -fm "$0")")")"
find $SRC -type f -name "*.nix" -exec nixfmt "$@" {} \;
