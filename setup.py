import os.path
from setuptools import setup

REQUIRES_PYTHON = ">=3.9.0"

HERE = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(HERE, "README.md"), encoding="utf-8") as fid:
    README = fid.read()

with open(os.path.join(HERE, "requirements.txt")) as fid:
    REQUIREMENTS = [req for req in fid.read().split("\n") if req]

from ev3sim import __version__

setup(
    name="ev3sim",
    version=__version__,
    description="Simulate ev3dev programs in Python",
    long_description=README,
    long_description_content_type="text/markdown",
    python_requires=REQUIRES_PYTHON,
    url="https://github.com/MelbourneHighSchoolRobotics/ev3sim",
    author="Jackson Goerner, James Bui, Richard Huang, Angus Trau, Peter Drew",
    author_email="jgoerner@outlook.com, jtbui20@gmail.com, me@huangrichard.com, contact@angus.ws, peter@pdrew.com",
    license="BSD-3-Clause",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Framework :: Robot Framework",
        "Framework :: Robot Framework :: Tool",
        "Topic :: Software Development :: Libraries :: pygame",
        "Topic :: Software Development :: Testing :: Mocking",
    ],
    packages=["ev3sim"],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    entry_points={
        "gui_scripts": [
            "ev3sim=ev3sim.entry:main",
        ]
    },
)
