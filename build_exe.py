import os
import shutil
from subprocess import Popen
from ev3sim import __version__

# First, generate the version file to be used in generation.
with open("version_file_template.txt", "r") as f:
    string = f.read().replace("<VERSION_NUMBER>", __version__)
with open("version_file.txt", "w") as f:
    f.write(string)

def generalBuild(arch): 
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    os.makedirs("dist", exist_ok=True)

    insertPythonEmbed(arch)
    insertClonedRepo()

    process = Popen(["makensis", "config.nsi"])
    process.wait()
    shutil.move("installer.exe", f"installer-{arch}bit.exe")

def insertPythonEmbed(arch):
    if os.path.exists("dist/python_embed"):
        shutil.rmtree("dist/python_embed")
    shutil.copytree(f"python_embed-{arch}", "dist/python_embed")

def insertClonedRepo():
    shutil.copytree(f"../ev3sim_clone", "dist/ev3sim")

if __name__ == "__main__":
    generalBuild(32)
    generalBuild(64)
