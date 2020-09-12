import numpy as np
from ev3sim.devices.base import IDeviceInteractor, Device
from ev3sim.devices.compass.base import CompassSensorMixin
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.devices.utils import NearestValue, CyclicMixin, RandomDistributionMixin


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

    calced_before = False

    # Generate 31 (Really 30) static points of interest that the compass jumps to.
    NEAREST_POINTS_AMOUNT = 31
    # The distribution variance of the nearest points
    NEAREST_POINTS_VARIANCE = 16

    # Maximum bias towards one direction, in degrees.
    MAX_SENSOR_OFFSET = 5

    def _calc(self):
        if not self.calced_before:
            if ScriptLoader.RANDOMISE_SENSORS:
                # Distribute cyclically between 0 and 360, generating 31 points with variance 16
                # This means on average about 12 degrees per step.
                self.dist = CompassValueDistribution(
                    0, 360, self.NEAREST_POINTS_AMOUNT, self.NEAREST_POINTS_VARIANCE, Randomiser.getPortRandom(self._interactor.port_key)
                )
                # +- 5 degrees offset.
                self.offset = (0.5 - self._interactor.random()) * 2 * self.MAX_SENSOR_OFFSET
            else:
                self.dist = CompassValueDistributionNoRandom(0, 360, self.NEAREST_POINTS_AMOUNT)
                self.offset = 0
            self.calced_before = True
        self._value = int(self.dist.get_closest(self._getValue() + self.offset))

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
