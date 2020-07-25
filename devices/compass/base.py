import numpy as np

class CompassSensorMixin:

    relative = 0

    def _setRelative(self):
        self.relative = self.global_rotation

    def _getValue(self):
        r = (self.global_rotation - self.relative) * 180 / np.pi
        while r < 0:
            r += 360
        while r >= 360:
            r -= 360
        return r
