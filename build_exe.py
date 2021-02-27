import argparse, sys
import PyInstaller.__main__
from subprocess import Popen
from ev3sim import __version__

parse = argparse.ArgumentParser()
parse.add_argument("--admin", action="store_true", dest="admin")

res = parse.parse_args(sys.argv[1:])

# First, generate the version file to be used in generation.
with open("version_file_template.txt", "r") as f:
    string = f.read().replace("<VERSION_NUMBER>", __version__)
with open("version_file.txt", "w") as f:
    f.write(string)

# Then generate the build.
PyInstaller.__main__.run(
    [
        "-y",
        "executable_entry.spec",
    ]
)

import os

if os.path.exists("dist/ev3sim/ev3sim/user_config.yaml"):
    os.remove("dist/ev3sim/ev3sim/user_config.yaml")

if res.admin:
    process = Popen("makensis config.nsi")
else:
    process = Popen("makensis config-no-admin.nsi")
process.wait()
