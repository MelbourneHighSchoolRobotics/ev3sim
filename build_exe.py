import PyInstaller.__main__
from subprocess import Popen
from ev3sim import __version__

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

process = Popen("makensis config.nsi")
process.wait()
