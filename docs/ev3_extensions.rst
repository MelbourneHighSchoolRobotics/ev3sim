Extensions to normal EV3 Code
=============================

Simulation testing
------------------

Since you should be able to use the same code on simulator as on your physical bot, some changes need to be made so the script can detect whether it is running in a simulated environment.
As an example, the simulator currently does not implement the ``Led`` functionality from ev3dev2, and so we need to ensure we are not in the simulator when calling ``Led`` functions.

.. code-block:: python

    from ev3dev2.led import Leds
    from ev3sim.code_helpers import is_ev3, is_sim

    if is_ev3:
        l = Leds()
        l.set_color('LEFT', 'AMBER')
    if is_sim:
        print("Hello from the sim! Sadly I can't do lights at the moment :(")

Importing this means you need to transfer ``ev3sim/code_helpers.py`` onto the brick for this to run (Just create a folder named ``ev3sim`` and place `code_helpers.py`_ in there).

.. _code_helpers.py: https://github.com/MelbourneHighSchool/RoboCup_Simulator/tree/main/ev3sim/code_helpers.py