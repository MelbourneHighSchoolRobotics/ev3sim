Setting up and Running EV3Sim
=============================

Installation
------------

You can install this package using pip as follows:

.. code-block:: bash

    python -m pip install ev3sim

After this, any new command prompt or terminal opened should have access to two new commands, ``ev3sim`` and ``ev3attach``.

You can check this is the case by opening command prompt and typing ``ev3sim -h``. You should get some explanation of the use of this program.

Running EV3Sim
--------------

Running the simulator is as simple as

.. code-block:: bash

    ev3sim bot.yaml

Which runs a simple soccer simulation, with 1 bot. You can define your own bots, by creating a ``.yaml`` file (Base this on `bot.yaml`_)

Attaching some code to bots in the simulation is then done by

.. code-block:: bash

    ev3attach demo.py Robot-0

Which, provided a simulation is already running, attaches some demo code to that robot. You can use your own ev3dev2 code instead of ``demo.py``, and right clicking a robot in the simulation will copy it's ID to the clipboard, so you can specify which robot to attach to, rather than ``Robot-0``.

More information on the use of these commands can be given with ``ev3sim -h`` or ``ev3attach -h``.

.. _bot.yaml: https://github.com/MelbourneHighSchoolRobotics/RoboCup_Simulator/tree/main/ev3sim/robots/bot.yaml
