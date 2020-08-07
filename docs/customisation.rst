Customising Bots and Maps
=========================

Bot Definitions
---------------

As was shown in the setup documentation, you can specify the bot spawned when passed into ``ev3sim``: 

.. code-block:: bash

    ev3sim bot.yaml

This ``.yaml`` file can define the location of sensors and many other things for each bot. (*Note*: this ``bot.yaml`` can be in your current working directory, or in a folder named ``robots`` and it will be recognised by the script.)

Some example structure of this ``.yaml`` file is as follows:

.. code-block:: yaml

    robot_class: ev3sim.robot.Robot
    devices:
    - LargeMotor:
      position: [0, 5]
      rotation: 0
      port: outB
    - UltrasonicSensor:
      position: [10, 0]
      rotation: 0
      port: in3
    base_plate:
      collider: inherit
      visual:
        name: Circle
        radius: 11
        fill: '#878E88'
        stroke_width: 0.1
        stroke: '#ffffff'
        zPos: 2
      mass: 5
      restitution: 0.2
      friction: 0.8
      children:
      - physics: false
        type: object
        visual:
          name: Image
          image_path: 'LogoTransparent.png'
          zPos: 2.05
          position: [4.5, 4.5]

* ``robot_class``: Points to the :doc:`/robot` class controlling this bot. Unless you are doing some specific to the bot (Like controlling with key presses), you should not have this line in your ``.yaml`` - It defaults to ``ev3sim.robot.Robot``.
* ``devices``: Describes all sensors and motors, their relative position and rotation. :doc:`/devices` gives a full list of what devices you can use.
* ``base_plate``: Describes the plate the devices are placed on. :doc:`/visual` gives a full list of what shapes you can make. At the moment children cannot have physics (and therefore a collider).

Simulation Definitions
----------------------

The simulator, while built for soccer, should be able to handle many other areas of robotics that can be simulated in 2d, provided they are well defined.

TODO