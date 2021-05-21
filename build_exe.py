import os
import shutil
from subprocess import Popen
from ev3sim import __version__

# First, generate the version file to be used in generation.
with open("version_file_template.txt", "r") as f:
    string = f.read().replace("<VERSION_NUMBER>", __version__)
with open("version_file.txt", "w") as f:
    f.write(string)

os.makedirs("dist", exist_ok=True)
os.makedirs("dist/ev3sim", exist_ok=True)
shutil.rmtree("dist/python_embed")
shutil.copytree("python_embed", "dist/python_embed")

if os.path.exists("dist/ev3sim/user_config.yaml"):
    os.remove("dist/ev3sim/user_config.yaml")

process = Popen("makensis config.nsi")
process.wait()
