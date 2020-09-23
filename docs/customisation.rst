Customising Bots and Maps
=========================

Bot Definitions
---------------

As was shown in the setup documentation, you can specify the bot(s) spawned when passed into ``ev3sim``: 

.. code-block:: bash

    ev3sim bot.yaml

This ``.yaml`` file can define the location of sensors and many other things for each bot. (*Note*: this ``bot.yaml`` can be in your current working directory, or in a folder named ``robots`` and it will be recognised by the script.)

Some example structure of this ``.yaml`` file is as follows:

.. code-block:: yaml

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
      - physics: true
        collider: inherit
        type: object
        visual:
          name: Rectangle
          width: 6
          height: 4
          zPos: 2.05
          position: [13, 0]

Try the above robot by pasting this into a ``.yaml`` file and invoking ``ev3sim`` with it as an argument! To describe what this ``.yaml`` file is providing:

* ``devices``: Describes all sensors and motors, their relative position and rotation. :doc:`/devices` gives a full list of what devices you can use.
* ``base_plate``: Describes the plate the devices are placed on. :doc:`/visual` gives a full list of what shapes you can make. At the moment children cannot have physics (and therefore a collider).

The rotation of all elements is measured in degrees, where 0 bearing is pointing to the right of the screen (which is assumed to be the front of the bot), and positive degrees indicated a counter-clockwise rotation.

Buttons
-------

In addition to the usual devices, you can also add working buttons to your robot which can be interacted with as you normally do on ev3dev2.
Just like with the devices, you specify a position, rotation, and port for the button. The port value determines which button this is recognised as, and can be ``up``, ``down``, ``left``, ``right``, ``enter`` or ``backspace``.

.. code-block:: yaml

  devices:
  - Button:
    position: [5, 0]
    rotation: 0
    port: enter

Interacting with this button is as usual on the ev3dev2 code:

.. code-block:: python

    from ev3dev2.button import Button
    from ev3sim.code_helpers import wait_for_tick

    buttons = Button()

    def state_change(state):
        if state is True:
            print("Enter pressed!")
        else:
            print("Enter released!")

    buttons.on_enter = state_change

    while True:
        if buttons.up:
            print("Up is being pressed!")
        buttons.process()
        wait_for_tick()

Simulation Definitions
----------------------

The simulator, while built for soccer, should be able to handle many other areas of robotics that can be simulated in 2d, provided they are well defined.

All of the logic running the soccer simulation in particular is defined in a **preset**. A preset is defined in ``.yaml`` as well, although the file tends to be much larger. It is split up into five sections:

.. code-block:: yaml

    colours:
      wall_color: "#2a9d8f"
      strip_color: "#f1faee"
      ...
    
    interactors:
    - class_path: presets.pick_up_interactor.PickUpInteractor
    - class_path: presets.pause_interactor.PauseInteractor
    - class_path: custom.MyCustomInteractor
    - ...
  
    settings:
      # ScriptLoader
      ev3sim.simulation.loader.ScriptLoader.GAME_TICK_RATE: 30
      ev3sim.simulation.loader.ScriptLoader.VISUAL_TICK_RATE: 30
      ev3sim.simulation.loader.ScriptLoader.TIME_SCALE: 1
      # ScreenManager
      ev3sim.visual.manager.ScreenObjectManager.SCREEN_WIDTH: 1280
      ev3sim.visual.manager.ScreenObjectManager.SCREEN_HEIGHT: 960
      ev3sim.visual.manager.ScreenObjectManager.MAP_WIDTH: 293.3
      ev3sim.visual.manager.ScreenObjectManager.MAP_HEIGHT: 220
      ev3sim.visual.manager.ScreenObjectManager.BACKGROUND_COLOUR: "#1f1f1f"
      # Soccer
      ev3sim.presets.soccer.SoccerInteractor.TEAM_NAMES:
        - Team 1
        - Team 2
      ev3sim.presets.soccer.SoccerInteractor.SPAWN_LOCATIONS:
        - [[[-80, -18], 0], [[-50, -18], 0]]
        - [[[80, -18], 180], [[50, -18], 180]]
      ev3sim.presets.soccer.SoccerInteractor.GOALS:
        - name: Rectangle
          width: 7.4
          height: 45
          position: [-95.2, -18]
          fill: goal_fill
        - name: Rectangle
          width: 7.4
          height: 45
          position: [95.2, -18]
          fill: goal_fill
      ev3sim.presets.soccer.SoccerInteractor.SHOW_GOAL_COLLIDERS: true

    elements:
    - type: visual
      name: Rectangle
      width: 243
      height: 183
      fill: 'wall_color'
      stroke_width: 0
      position: [0, -18]
      zPos: 3
      key: grass
      sensorVisible: true
    - ...

* ``colours``: This defines a few colours which might be repeated in the definition of items, for example if you want to draw multiple walls.
* ``interactors``: This points to any :doc:`/interactor` which should be active when running the simulation.
* ``settings``: Can redefine essentially any one of the simulator constants. You can delve into the codebase if you want to change particular things or you can just change existing settings in the yaml.
* ``elements``: This defines all visual and physical objects spawned in the preset. ``sensorVisible`` is true if a colour sensor should pick up this object.

A full example of the soccer preset can be found `here`_.

.. _here: https://github.com/MelbourneHighSchoolRobotics/ev3sim/tree/main/ev3sim/presets/soccer.yaml

After saving this to ``preset.yaml`` for example, you can run the simulation with this preset by running

.. code-block:: bash

    ev3sim --preset=preset.yaml bot.yaml
