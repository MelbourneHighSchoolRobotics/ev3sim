import numpy as np
from ev3sim.objects.utils import magnitude_sq
from ev3sim.devices.base import IDeviceInteractor, Device
from ev3sim.devices.infrared.base import InfraredSensorMixin
from ev3sim.simulation.loader import ScriptLoader


class InfraredInteractor(IDeviceInteractor):

    name = "INFRARED"

    def startUp(self):
        super().startUp()
        self.tracking_ball = ScriptLoader.instance.object_map["IR_BALL"]

    def tick(self, tick):
        ball_pos = self.tracking_ball.position
        sensor = ScriptLoader.instance.object_map[self.getPrefix() + "light_up_2"]
        distance = np.sqrt(magnitude_sq(ball_pos - sensor.position))
        vector = ball_pos - sensor.position
        relative_bearing = np.arctan2(vector[1], vector[0]) - sensor.rotation
        self.device_class._calc(relative_bearing, distance)
        for x in range(5):
            ScriptLoader.instance.object_map[self.getPrefix() + f"light_up_{x}"].visual.fill = (
                max(min(255 * self.device_class.value(x + 1) / 9, 255), 0),
                0,
                0,
            )
        return False


class InfraredSensor(InfraredSensorMixin, Device):
    """
    Infrared Sensor can detect the soccer ball in a cone of vision, and has 5 small sensors which aggregate to localise the ball.
    (More generally, it can detect any physical object with tag 'IR_BALL')

    It has one method, `value`, whose input can be 0-6, returning different sensor data.
    """

    def _calc(self, relativeBearing, distance):
        self._values = self._sensorValues(relativeBearing, distance)

    def value(self, index):
        """
        Get sensor data.

        index=0:
            Get a crude direction prediction from the sensor.
            return 0: Ball lost
            return 1-9: Ball is (1: Far left) (...) (5: Centred) (...) (9: Far right)
        index=1-5:
            Get the sensor value on subsensor 1-5. Has a value ranging from 0-9.
            Sensor 1: Far left
            Sensor 2: Left
            Sensor 3: Middle
            Sensor 4: Right
            Sensor 5: Far right
        index=6:
            Get the average sensor value.

        Example usage:
        ```
        >>> print([ir.value(x) for x in range(1, 6)])
        [0, 4, 8, 4, 0]
        >>> print(ir.value(0))
        5
        >>> print(ir.value(6))
        3.2
        ```
        """
        if index == 0:
            return self._predict(self._values)
        if 1 <= index <= 5:
            return self._values[index - 1]
        if index == 6:
            return int(sum(self._values) / len(self._values))
        raise ValueError(f"Unknown value index {index}, should be an integer from 0-6.")
