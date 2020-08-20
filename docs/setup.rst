Setting up and Running EV3Sim
=============================

Installation
------------

EV3sim requires python 3.7+ installed on your system. If you don't already have it, you can download it from https://www.python.org/ .

You can install this package using pip as follows:

.. code-block:: bash

    python -m pip install ev3sim

After this, any new command prompt or terminal opened should have access to two new commands, ``ev3sim`` and ``ev3attach``.

You can check this is the case by opening command prompt and typing ``ev3sim -h``. You should get some explanation of the use of this program.

If it works, great! You should be ready to go. If not, there are some platform specific instructions further down. If that also doesn't work, contact one of the Melbourne High Robotics Mentors (or optionally, raise an issue on github! https://github.com/MelbourneHighSchoolRobotics/ev3sim)

Running EV3Sim
--------------

Running the simulator is as simple as

.. code-block:: bash

    ev3sim bot.yaml

Which runs a simple soccer simulation, with 1 bot. You can define your own bots, by creating a ``.yaml`` file (Base this on `bot.yaml`_)

Attaching some code to bots in the simulation is then done running the following in a new command prompt

.. code-block:: bash

    ev3attach demo.py Robot-0

Which, provided a simulation is already running, attaches some demo code to that robot. You can use your own ev3dev2 code instead of ``demo.py``, and right clicking a robot in the simulation will copy it's ID to the clipboard, so you can specify which robot to attach to, rather than ``Robot-0``.

More information on the use of these commands can be given with ``ev3sim -h`` or ``ev3attach -h``.

.. _bot.yaml: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/robots/bot.yaml


Further Information on installing
---------------------------------

Windows
^^^^^^^


Command not recognised
""""""""""""""""""""""

.. code-block:: batch

    'pip' is not recognized as an internal or external command, operable program, or batch file

Make sure you install python with the "Add python to PATH" option selected. This makes sure that the windows command line will understand the python and pip commands. For more information, see https://docs.python.org/3/using/windows.html#installation-steps


Ev3sim runs, but no pygame window is created
"""""""""""""""""""""""""""""""""""""""""""

This is a known issue with pygame. A possible cause is not having the English (US) Language pack in windows installed. This should install itself after a few minutes, once you've installed the package, but if that doesn't occur, you may wish to try manually installing it.

Unix
^^^^^^


Dependancy or binary package errors
"""""""""""""""""""""""""""""""""""

Pygame requires binary dependencies that aren't always installed by default.

Debian/Ubuntu/Mint


``sudo apt-get install python3-pygame``

Redhat/CentOS

``sudo yum install python3-pygame``

Arch 

``sudo pacman install python-pygame``
