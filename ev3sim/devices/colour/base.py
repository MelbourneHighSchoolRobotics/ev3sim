import numpy as np
from ev3sim.simulation.randomisation import Randomiser


class ColourSensorMixin:

    RGB_RAW = "RGB-RAW"
    COL_REFLECT = "COL-REFLECT"
    COL_COLOR = "COL-COLOR"

    device_type = "lego-sensor"
    mode = RGB_RAW

    SENSOR_RADIUS = 1
    SENSOR_POINTS = 100

    def _SenseValueAboutPosition(self, centrePosition, valueGetter):
        # Randomly sample value from SENSOR_POINTS chosen around the centrePosition.
        points = [Randomiser.random() * self.SENSOR_RADIUS for _ in range(self.SENSOR_POINTS)]
        for x in range(len(points)):
            angle = Randomiser.random() * 2 * np.pi
            points[x] = valueGetter(np.array([np.cos(angle) * points[x], np.cos(angle) * points[x]]) + centrePosition)
            # For some reason the color module hangs otherwise :/
            if hasattr(points[x], "r"):
                points[x] = np.array([points[x].r, points[x].g, points[x].b])
        total = points[0]
        for x in range(1, len(points)):
            total += points[x]
        return total / len(points)

    def _getObjName(self, port):
        return "sensor" + port

    def applyWrite(self, attribute, value):
        if attribute == "mode":
            self.mode = value
        else:
            raise ValueError(f"Unhandled write! {attribute} {value}")

    def toObject(self):
        res = self.raw()
        data = {
            "address": self._interactor.port,
            "driver_name": "lego-ev3-color",
            "mode": self.mode,
        }
        if self.mode == self.RGB_RAW:
            data["value0"], data["value1"], data["value2"] = res
        elif self.mode == self.COL_REFLECT:
            data["value0"] = self.reflected_light_intensity()
        elif self.mode == self.COL_COLOR:
            data["value0"] = self.predict_color()
        else:
            raise ValueError(f"Unhandled mode {self.mode}")
        return data
