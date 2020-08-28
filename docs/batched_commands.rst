Batched Commands
================

Running a batched command
-------------------------

In the previous document, we run the simulator and attach script logic in two separate terminals.

.. code-block:: bash

    ev3sim bot.yaml
    ev3attach demo.py Robot-0

When testing robot code, as well as competitions, many of these commands will be the same however, and it would be much easier if the entire simulation, with code running, could be invoked by a single command.
In fact, the simulator allows for this! 

To run the simulator with two bots both running the demo code, execute the following command:

.. code-block:: bash

    ev3sim -b soccer_competition.yaml

This ``-b`` or ``--batch`` flag specifies to use the file ``soccer_competition.yaml`` as the information for the simulator, as well as attaching code to bots.

Defining batched commands
-------------------------

You can write your own batched commands, just as you can write your own bot definitions and bot code. You can find the source for ``soccer_competition.yaml`` `here`_.

.. _here: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/batched_commands/soccer_competition.yaml

The batched command file looks like the following:

.. code-block:: yaml

    preset_file: soccer.yaml
    bots:
    - name: bot.yaml
      scripts:
      - demo.py
    - name: bot.yaml
      scripts:
      - demo.py

The ``preset_file`` points to the preset to load (usually specified with the ``-p`` flag in ``ev3sim``, but defaults to ``soccer.yaml``).
After this you can specify any boats to load, as well as scripts to attach to them.

Batched command problems
------------------------

Batched commands don't properly pipe the output of scripts/simulator to the terminal, and so shouldn't be used if you need to use the ``print`` function.

Additionally, if your computer is not powerful enough to run the number of bots specified with scripts attached, the command may just fail or hang. 
This method of loading robots is only supplied for ease of use, and has its problems.
