import math
import numpy as np
from objects.base import objectFactory
from simulation.world import World

class InfraredSensorMixin:

    # Left to Right, bearing relative to middle.
    SENSOR_BEARINGS = [
        np.pi/3,
        np.pi/6,
        0,
        -np.pi/6,
        -np.pi/3,
    ]

    SENSOR_BEARING_DROPOFF_MAX = np.pi/4

    MAX_SENSOR_RANGE = 120

    MAX_STRENGTH = 9

    def _sensorStrength(self, relativeBearing, distance):
        while relativeBearing > np.pi:
            relativeBearing -= 2*np.pi
        while relativeBearing < -np.pi:
            relativeBearing += 2*np.pi
        if distance > self.MAX_SENSOR_RANGE:
            return 0
        if abs(relativeBearing) > self.SENSOR_BEARING_DROPOFF_MAX:
            return 0
        # At halfway to the sensor, this value is 1/4.
        sq_dist = pow(distance / self.MAX_SENSOR_RANGE, 2)
        exclude_bearing = (1 - sq_dist) * 9
        bearing_mult = 1 - abs(relativeBearing) / self.SENSOR_BEARING_DROPOFF_MAX
        return math.floor(exclude_bearing * bearing_mult + 0.5)
    
    def _sensorValues(self, relativeBearing, distance):
        return [
            self._sensorStrength(relativeBearing-b, distance)
            for b in self.SENSOR_BEARINGS
        ]

    def _predict(self, sensorValues):
        total = sum(sensorValues)
        if total <= 4:
            return 0
        weighted = sum([
            i*v / total
            for i, v in enumerate(sensorValues)
        ])
        # weighted is between 0 and len(sensorValues)-1.
        return max(min(1 + math.floor(weighted / (len(sensorValues)-1) * 9), 9), 1)

