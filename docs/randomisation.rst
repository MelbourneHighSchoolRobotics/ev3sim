Randomisation
=============

TODO: Change this to gui docs

When executing ``ev3sim`` you may notice that the following is printed:

.. code-block:: bash

    Simulating with seed 0000000000

But with a different number to the one above. This number is the 'seed' and essentially defines all randomness that will occur within the system.

Despite being mostly the same on every run, some elements of the simulation require randomness, for realism, and to ensure that every run is slightly different:

* The spawn positions of bots and balls is slightly randomised.
* The way a colour sensor detects colours requires randomness.

As such in order to redo a simulation exactly as was done before, we want to be able to use the same seed, to ensure all random numbers are also the same.

You can do this with the ``--seed`` or ``-s`` flag in ``ev3sim``. As an example, to simulate with seed 123456789, you can do the following:

.. code-block:: bash

    ev3sim bot.yaml --seed 123456789

Note that the ``Simulating with seed`` line will respect this change. The seed can be any integer from 0 to 2^32 - 1, inclusive.

To make simulation of devices a bit more realistic, there is also support for the randomisation of device characteristics, in similar ways to what you might expect in real life. Examples include:

* Motors having a theoretical maximum speed, but also a physical one which differs slightly
* Sensors having slight biases towards certain directions

And you can enable this randomisation by using the ``soccer_random.yaml`` preset rather than ``soccer.yaml``:

.. code-block:: bash

    ev3sim bot.yaml --seed 123456789 -p soccer_random.yaml

To add randomisation to your particular preset, you only need to add the following:

.. code-block:: yaml

    settings:
      ev3sim.simulation.loader.ScriptLoader.RANDOMISE_SENSORS: true  

That being said, some of this randomisation is not done based on the seed, but rather the port and robot the device is connected to (This is to simulate you working with the same device with the same bias between runs). As a rule of thumb:

* Internal biases of devices will be static on the same port / robot filename.
* Randomness which is introduced over time or every game tick is tied to the seed.
