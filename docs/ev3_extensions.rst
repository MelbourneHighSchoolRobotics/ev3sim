Extensions to normal EV3 Code
=============================

While your robots still run python-ev3dev2 code in the simulation, you also have access to a few other bits of functionality not seen in a physical bot.

Almost all of the below functionality is available in the package ``ev3sim.code_helpers``. In order for this code to work on your physical robot, there also needs to be a package on the physical bot filesystem called ``ev3sim.code_helpers``, containing `this file`_.

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

Robot ID
--------

Since you might be running multiple instances of the same code on different robots, it's important to be able to check which robot the code is running on, you can do this with ``code_helpers``:

.. code-block:: python

    from ev3sim.code_helpers import robot_id

    print("Hello from " + robot_id)

This will also work on the brick, it should print "Robot-0".

Importing this means you need to transfer ``ev3sim/code_helpers.py`` onto the brick for this to run (Just create a folder named ``ev3sim`` and place `code_helpers.py`_ in there).

Printing to console
-------------------

Printing information is the simplest, quickest way to debug your code. Provided you have enabled the console in the settings of EV3Sim (It is enabled by default), you can print information to the console when simulating.

However, you can customise how your printed message looks on the screen using the code_helper function ``format_print``.

Bold, Italics, Colours
^^^^^^^^^^^^^^^^^^^^^^

You can use the ``<b>``, ``<i>`` and ``<font>`` tags to add styling to your message.
Example:

.. code-block:: python

    from ev3sim.code_helpers import format_print

    # The color specified below is a hex string.
    format_print("<b>Hello world!</b> I am <font color=\"#ff0000\">red</font> and <i>I slant</i>")

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Will print "**Hello world!** I am :red:`red` and *I slant*" in the simulator, but "Hello world! I am red and I slant" will be printed in real life (and the logs).

Life
^^^^

By default, after 3 seconds your print statement will vanish from the console. You can customise this time using the ``life`` key.
Example:

.. code-block:: python

    from ev3sim.code_helpers import format_print

    # This message will stay on the console for 3 seconds
    format_print("Hello world!")
    # This message will stay on the console for 5 seconds
    format_print("Hello world!", life=3)
    # This message will stay on the console for 1 second.
    format_print("Hello world!", life=1)

Alive ID
^^^^^^^^

Sometimes, you want a message to stay open on the console, and you might even want to change what is shown.
As an example, you might want to print your motor speeds every tick. In order to achieve this functionality, you can use the ``alive_id`` key when printing.
Example:

.. code-block:: python

    from ev3sim.code_helpers import wait_for_tick, robot_id, format_print

    x = 0
    while True:
        x += 0.001
        format_print(f"x value: {x:.2f}", alive_id=f"number-{robot_id}")
        wait_for_tick()

Logs
----

All prints made to the console will also be stored in log files. These log files are available in your workspace if the workspace is defined. Otherwise they will be stored in your EV3Sim install location.

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

Handling simulation events
--------------------------

While in simulation, for various reasons you might want to react to certain events occuring in the simulator.
As an example, your code may want to be aware of when an enemy (or you) has scored a goal, so you can change playstyle, or evaluate current strategy.

To handle such events you can use the code helpers EventSystem:

.. code-block:: python

    from ev3sim.code_helpers import EventSystem, wait_for_tick

    def handle_scored(data):
        if not data["against_you"]:
            print("I scored a goal!")
        else:
            print("No we let them score!")

    EventSystem.on_goal_scored = handle_scored

    while True:
        EventSystem.handle_events()
        wait_for_tick()

``EventSystem.handle_events`` must be called often (ie in every loop iteration, simply add this line after every occurrence of ``wait_for_tick``) to allow such events to fire the related code. Any event in the system returns a data object, which will contain any useful information about the event.

Importing this means you need to transfer ``ev3sim/code_helpers.py`` onto the brick for this to run (Just create a folder named ``ev3sim`` and place `code_helpers.py`_ in there).

The full list of events is:

``on_goal_scored``
^^^^^^^^^^^^^^^^^^
Fires whenever a goal is scored by either team.

* ``against_you``: True if the enemy team scored against you. False otherwise.

``on_reset``
^^^^^^^^^^^^
Fires whenever the game is reset manually.

``on_penalty_start``
^^^^^^^^^^^^^^^^^^
Fires whenever you are placed in the penalty box.

``on_penalty_end``
^^^^^^^^^^^^^^^^^^
Fires whenever you are removed from the penalty box.

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

For an example of robots communicating device data to each other (in this case through a server, but client/server messaging could also simply work between two robots) try this example (place all 4 commands in separate terminals), you can run the simulation preset ``ev3sim/examples/sims/communications_demo.yaml``

Sources: `communication_client.py`_, `communication_server.py`_

.. _this file: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/code_helpers.py
.. _code_helpers.py: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/code_helpers.py
.. _communication_client.py: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/robots/communication_client.py
.. _communication_server.py: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/robots/communication_server.py