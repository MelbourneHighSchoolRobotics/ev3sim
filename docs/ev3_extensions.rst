Extensions to normal EV3 Code
=============================

Waiting for simulation ticks
----------------------------

As most ev3 programs tend to have a single loop which handles all of the robot's logic, in the interest of efficiency on simulator we highly recommend you attempt to sync this program loop up with each tick of the simulator.
This is because running multiple program loops per simulation tick is useless (as sensor values won't change) and it can degrade the reliability of sensor values in future, if this program is spending a lot of CPU time running these pointless loops.

You can achieve such a sync with the ``wait_for_tick`` method from the code helpers:

.. code-block:: python

    from ev3sim.code_helpers import wait_for_tick

    while True:
        # Program logic...
        wait_for_tick()

Importing this means you need to transfer ``ev3sim/code_helpers.py`` onto the brick for this to run (Just create a folder named ``ev3sim`` and place `code_helpers.py`_ in there).

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

.. _code_helpers.py: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/code_helpers.py

Robot Communications
--------------------

As bluetooth communications are a popular option for complicated strategies with robots, there is also functionality to support bot communication on the simulator.

.. code-block:: python

    # Server code
    from ev3sim.code_helpers import CommServer
    addr, port = 'aa:bb:cc:dd:ee:ff', 1234

    server = CommServer(addr, port)
    client, info = server.accept_client()

    print(f"Message from client: {client.recv(1024)}")

    # Client code
    from ev3sim.code_helpers import CommClient
    addr, port = 'aa:bb:cc:dd:ee:ff', 1234

    client = CommClient(addr, port)
    client.send("Hello Server!")

The communications are written in a client/server architecture, as with normal use of bluetooth comms.

This should also work on the physical robots over bluetooth, provided that the MAC Address and port are correct (Follow the instructions for normal bluetooth connectivity). As with above importing this means you need to transfer ``ev3sim/code_helpers.py`` onto the brick for this to run (Just create a folder named ``ev3sim`` and place `code_helpers.py`_ in there).

For an example of robots communicating device data to each other (in this case through a server, but client/server messaging could also simply work between two robots) try this example (place all 4 commands in separate terminals):

.. code-block:: bash

    ev3sim bot.yaml bot.yaml bot.yaml
.. code-block:: bash

    ev3attach communication_client.py Robot-0
.. code-block:: bash

    ev3attach communication_server.py Robot-1
.. code-block:: bash

    ev3attach communication_client.py Robot-2

Sources: `communication_client.py`_, `communication_server.py`_

.. _communication_client.py: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/robots/communication_client.py
.. _communication_server.py: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/robots/communication_server.py
