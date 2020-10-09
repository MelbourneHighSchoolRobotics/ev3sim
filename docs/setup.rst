Setting up and Running EV3Sim
=============================

Installation
------------

EV3sim requires Python 3.7-3.8 (3.9 is currently unsupported and will not work) to be installed on your system. If you don't already have Python installed, you can download it from https://www.python.org/ .

You can install this package using pip as follows:

.. code-block:: bash

    python -m pip install -U ev3sim

(This command also updates ev3sim if you already have it installed.)

After this, any new command prompt or terminal opened should have access to two new commands, ``ev3sim`` and ``ev3attach``.

You can check this is the case by opening command prompt and typing ``ev3sim -h``. You should get some explanation of the use of this program.

If it works, great! You should be ready to go. If not, there are some platform specific instructions further down. If that also doesn't work, contact one of the Melbourne High Robotics Mentors (or optionally, raise an issue on github! https://github.com/MelbourneHighSchoolRobotics/ev3sim)

Occasionally, you may need to run this command again to update the simulator.

Running EV3Sim
--------------

Running the simulator is as simple running the following command in the command line: 

.. code-block:: bash

    ev3sim bot.yaml

This runs a simple soccer simulation, with 1 bot. bot.yaml is a pre-made bot included with the package, for demonstration purposes.

This should open a new pygame window with the simulation, as follows:

.. image:: images/sim.jpg
  :width: 600
  :alt: The pygame window for the simulator

You can also run the simulator with a robot that is contrlled by the keyboard: 

.. code-block:: bash

    ev3sim controllable.yaml

You can define and run your own bots, by creating a ``.yaml`` file (Base this on `bot.yaml`_). Navigate to your yaml file in the command line (either by opening the command line window in the appropriate directory, or using ``cd`` (change directory) and ``dir/ls`` (list directory)

If you want to run the simulation with multiple bots, you can simply add more yaml files to the command.

.. code-block:: bash

    ev3sim bot.yaml bot.yaml bot.yaml bot.yaml

Attaching some code to bots in the simulation is then done running the following in a new command prompt

.. code-block:: bash

    ev3attach demo.py Robot-0

Which, provided a simulation is already running, attaches some demo code to that robot. Each robot has a unique ID that you can use to attach your own code to, starting from 0. You can right click on a robot in the simulation to copy it's ID to the clipboard, so you can specify which robot to attach to, rahter than ``Robot-0``.


This is much the same as the previous command, where you need to be in the appropriate directory. You can use your own ev3dev2 code instead of ``demo.py``

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
"""""""""""""""""""""""""""""""""""""""""""""""""

This is a known issue with pygame. A possible cause is not having the English (US) Language pack in windows installed. This should install itself after a few minutes, once you've installed the package, but if that doesn't occur, you may wish to try manually installing it.

Unix
^^^^^


Dependancy or binary package errors
""""""""""""""""""""""""""""""""""""""""

Pygame requires binary dependencies that aren't always installed by default.

Debian/Ubuntu/Mint


``sudo apt-get install python3-pygame``

Redhat/CentOS

``sudo yum install python3-pygame``

Arch 

``sudo pacman -S python-pygame``
