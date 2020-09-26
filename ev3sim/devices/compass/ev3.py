import numpy as np
from ev3sim.devices.base import IDeviceInteractor, Device
from ev3sim.devices.compass.base import CompassSensorMixin
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.devices.utils import NearestValue, CyclicMixin, RandomDistributionMixin
from opensimplex import OpenSimplex


class CompassInteractor(IDeviceInteractor):

    name = "COMPASS"

    def tick(self, tick):
        self.device_class._calc()
        self.do_rotation = self.device_class.value() * np.pi / 180

    def afterPhysics(self):
        for i, obj in enumerate(self.generated):
            obj.position = local_space_to_world_space(
                self.relative_location
                + local_space_to_world_space(self.relative_positions[i], self.relative_rotation, np.array([0, 0])),
                self.physical_object.rotation,
                self.physical_object.position,
            )
            if obj.key == (self.getPrefix() + "relative_north"):
                obj.rotation = self.device_class.global_rotation - self.do_rotation
            else:
                obj.rotation = self.physical_object.rotation + self.relative_rotation


class CompassValueDistribution(CyclicMixin, RandomDistributionMixin, NearestValue):
    pass


class CompassValueDistributionNoRandom(CyclicMixin, NearestValue):
    pass


class CompassSensor(CompassSensorMixin, Device):
    """
    EV3 Compass Sensor, calculates the bearing of the device relative to some direction (which can be specified).

    To get this bearing, use `value`.

    To set the relative heading of the sensor, use `calibrate`.
    """

    # Generate 31 (Really 30) static points of interest that the compass jumps to.
    NEAREST_POINTS_NUMBER = 51
    # The distribution variance of the nearest points
    NEAREST_POINTS_VARIANCE = 16

    # Random noise on the compass sensor moves along time in the x direction.
    # Every time calibrate is called a new y position is set.
    # Because noise is continuous, a device might only have a few patterns of offset if we restrict the y position.
    NOISE_SAMPLE_HEIGHT = 5
    NOISE_WIDTH_PER_TICK = 0.03
    NOISE_AMPLIFIER = 0.2
    NOISE_Y_OFFSET_MAX = 10000
    NOISE_EFFECT_MAX = 15

    # Maximum bias towards one direction, in degrees.
    MAX_SENSOR_OFFSET = 5

    def generateBias(self):
        if ScriptLoader.RANDOMISE_SENSORS:
            # Distribute points cyclically between 0 and 360.
            self.dist = CompassValueDistribution(
                0,
                360,
                self.NEAREST_POINTS_NUMBER,
                self.NEAREST_POINTS_VARIANCE,
                Randomiser.getPortRandom(self._interactor.port_key),
            )
        else:
            self.dist = CompassValueDistributionNoRandom(0, 360, self.NEAREST_POINTS_NUMBER)
        self.current_offset = 0
        self.device_y_offset = self.NOISE_Y_OFFSET_MAX * self._interactor.random()
        self.noise_tick = 0
        self._value = 0
        self.noise = OpenSimplex(seed=Randomiser.getInstance().seeds[self._interactor.port_key])
        self.calibrate()

    def _calc(self):
        noise = self.noise.noise2d(
            x=self.noise_tick * self.NOISE_WIDTH_PER_TICK, y=self.current_sample_point + self.device_y_offset
        )
        self.current_offset += noise * self.NOISE_AMPLIFIER
        self.current_offset = min(max(self.current_offset, -self.NOISE_EFFECT_MAX), self.NOISE_EFFECT_MAX)
        self.noise_tick += 1
        add_offset = self.dist.get_closest(self._getValue()) + self.current_offset
        add_offset %= 360
        self._value = int(add_offset)

    def value(self):
        """
        Get the compass value.

        :returns: Value from 0 to 360, which is the relative bearing (measured anticlockwise from the true bearing).

        Example usage:
        ```
        >>> print(compass.value())
        48.2
        ```
        """
        return self._value

    def calibrate(self):
        """
        Set the sensor so the current bearing is interpreted as 0.

        Example usage:
        ```
        >>> compass.calibrate()
        >>> # Rotates 10 degrees to the left
        >>> compass.value()
        10
        ```
        """
        self._setRelative()
        self.current_offset = 0
        self.current_sample_point = Randomiser.random() * self.NOISE_SAMPLE_HEIGHT
