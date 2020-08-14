import numpy as np
from ev3sim.devices.base import IDeviceInteractor, Device
from ev3sim.devices.compass.base import CompassSensorMixin
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.simulation.loader import ScriptLoader

class CompassInteractor(IDeviceInteractor):

    name = 'COMPASS'

    def tick(self, tick):
        self.device_class._calc()
        self.do_rotation = self.device_class.value() * np.pi / 180
    
    def afterPhysics(self):
        for i, obj in enumerate(self.generated):
            obj.position = local_space_to_world_space(
                self.relative_location + local_space_to_world_space(self.relative_positions[i], self.relative_rotation, np.array([0 ,0])), 
                self.physical_object.rotation, 
                self.physical_object.position,
            )
            if obj.key == (self.getPrefix() + 'relative_north'):
                obj.rotation = self.device_class.global_rotation - self.do_rotation
            else:
                obj.rotation = self.physical_object.rotation + self.relative_rotation

class CompassSensor(CompassSensorMixin, Device):
    """
    EV3 Compass Sensor, calculates the bearing of the device relative to some direction (which can be specified).

    To get this bearing, use `value`.

    To set the relative heading of the sensor, use `calibrate`.
    """

    def _calc(self):
        self._value = int(self._getValue())

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