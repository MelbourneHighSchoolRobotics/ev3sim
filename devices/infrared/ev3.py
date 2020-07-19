import numpy as np
from objects.utils import magnitude_sq
from devices.base import IDeviceInteractor, Device
from devices.infrared.base import InfraredSensorMixin
from simulation.loader import ScriptLoader

class InfraredInteractor(IDeviceInteractor):

    name = 'INFRARED'

    def startUp(self):
        super().startUp()
        self.tracking_ball = ScriptLoader.instance.object_map['IR_BALL']

    def tick(self, tick):
        ball_pos = self.tracking_ball.position
        sensor = ScriptLoader.instance.object_map[self.getPrefix() + 'light_up_2']
        distance = np.sqrt(magnitude_sq(ball_pos - sensor.position))
        vector = ball_pos - sensor.position
        relative_bearing = np.arccos(vector[0]/np.sqrt(magnitude_sq(vector))) - sensor.rotation
        self.device_class.calc(relative_bearing, distance)
        for x in range(5):
            ScriptLoader.instance.object_map[self.getPrefix() + f'light_up_{x}'].visual.fill = (max(min(255 * self.device_class.value(x+1) / 9, 255), 0), 0, 0)
        return False

class InfraredSensor(Device, InfraredSensorMixin):

    def calc(self, relativeBearing, distance):
        self._values = self._sensorValues(relativeBearing, distance)
    
    def value(self, index):
        if index == 0:
            return self._predict()
        if 1 <= index <= 5:
            return self._values[index-1]
        if index == 6:
            return sum(self._values) / len(self._values)
        raise ValueError(f"Unknown value index {index}, should be an integer from 0-6.")