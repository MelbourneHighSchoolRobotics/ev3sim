import numpy as np


class CompassSensorMixin:

    device_type = "lego-sensor"

    relative = 0
    mode = "COMPASS"

    def _setRelative(self):
        self.relative = self.global_rotation

    def _getValue(self):
        r = (self.global_rotation - self.relative) * 180 / np.pi
        while r < 0:
            r += 360
        while r >= 360:
            r -= 360
        return r

    def _getObjName(self, port):
        return "sensor" + port

    def applyWrite(self, attribute, value):
        if attribute == "mode":
            self.mode = value
        elif attribute == "command":
            if value == "BEGIN-CAL":
                self._setRelative()
            elif value == "END-CAL":
                pass
            else:
                raise ValueError(f"Unknown compass command {value}")
        else:
            raise ValueError(f"Unhandled write! {attribute} {value}")

    def toObject(self):
        return {
            "address": self._interactor.port,
            "driver_name": "ht-nxt-compass",
            "mode": self.mode,
            "value0": self.value(),
            "decimals": 0,
        }
