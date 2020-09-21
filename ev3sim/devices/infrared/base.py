import math
import numpy as np
from ev3sim.objects.base import objectFactory
from ev3sim.simulation.world import World
from ev3sim.simulation.loader import ScriptLoader


class InfraredSensorMixin:

    device_type = "lego-sensor"

    ALL_VALUES = "AC-ALL"
    DIRECTION = "AC"
    ALL_VALUES_DC = "DC-ALL"
    DIRECTION_DC = "DC"

    mode = ALL_VALUES

    # Left to Right, bearing relative to middle.
    SENSOR_BEARINGS = [
        np.pi / 3,
        np.pi / 6,
        0,
        -np.pi / 6,
        -np.pi / 3,
    ]

    SENSOR_BEARING_DROPOFF_MAX = np.pi / 4

    MAX_SENSOR_RANGE = 120

    MAX_STRENGTH = 9

    SUBSENSOR_BIAS_MAGNITUDE = 5

    def generateBias(self):
        self.distance_biases = [
            (0.5 - self._interactor.random()) * 2 * self.SUBSENSOR_BIAS_MAGNITUDE
            if ScriptLoader.RANDOMISE_SENSORS
            else 0
            for _ in range(5)
        ]
        self._values = [0 for _ in self.SENSOR_BEARINGS]

    def _sensorStrength(self, relativeBearing, distance, sensorIndex):
        perceived_distance = max(distance + self.distance_biases[sensorIndex], 0)
        while relativeBearing > np.pi:
            relativeBearing -= 2 * np.pi
        while relativeBearing < -np.pi:
            relativeBearing += 2 * np.pi
        if perceived_distance > self.MAX_SENSOR_RANGE:
            return 0
        if abs(relativeBearing) > self.SENSOR_BEARING_DROPOFF_MAX:
            return 0
        # At halfway to the sensor, this value is 1/4.
        sq_dist = pow(perceived_distance / self.MAX_SENSOR_RANGE, 2)
        exclude_bearing = (1 - sq_dist) * self.MAX_STRENGTH
        bearing_mult = 1 - abs(relativeBearing) / self.SENSOR_BEARING_DROPOFF_MAX
        return int(math.floor(exclude_bearing * bearing_mult + 0.5))

    def _sensorValues(self, relativeBearing, distance):
        return [self._sensorStrength(relativeBearing - b, distance, i) for i, b in enumerate(self.SENSOR_BEARINGS)]

    def _predict(self, sensorValues):
        total = sum(sensorValues)
        if total <= 4:
            return 0
        weighted = sum([i * v / total for i, v in enumerate(sensorValues)])
        # weighted is between 0 and len(sensorValues)-1.
        return int(max(min(1 + math.floor(weighted / (len(sensorValues) - 1) * 9), 9), 1))

    def _getObjName(self, port):
        return "sensor" + port

    def applyWrite(self, attribute, value):
        if attribute == "mode":
            self.mode = value
        else:
            raise ValueError(f"Unhandled write! {attribute} {value}")

    def toObject(self):
        data = {
            "address": self._interactor.port,
            "driver_name": "ht-nxt-ir-seek-v2",
            "mode": self.mode,
        }
        if self.mode == self.ALL_VALUES:
            for x in range(7):
                data[f"value{x}"] = self.value(x)
        elif self.mode == self.DIRECTION:
            data["value0"] = self.value(0)
        elif self.mode == self.ALL_VALUES_DC:
            for x in range(7):
                data[f"value{x}"] = 0
        elif self.mode == self.DIRECTION_DC:
            data["value0"] = 0
        else:
            raise ValueError(f"Unhandled mode {self.mode}")
        return data
