import numpy as np
from simulation.loader import ScriptLoader

class MotorMixin:

    MAX_FORCE = 10000
    time_wait = -1

    applied_force = 0

    def _updateTime(self, tick):
        if self.time_wait > 0:
            self.time_wait -= 1 / ScriptLoader.instance.GAME_TICK_RATE
            if self.time_wait <= 0:
                self.off()
    
    def _applyMotors(self, object, position, rotation):
        object.apply_force(self.applied_force * np.array([np.cos(rotation), np.sin(rotation)]), pos=position)

    def on(self, speed, **kwargs):
        assert - 100 <= speed <= 100, "Speed value is out of bounds."
        self.applied_force = speed * self.MAX_FORCE / 100

    def on_for_seconds(self, speed, seconds, **kwargs):
        self.on(speed, **kwargs)
        self.time_wait = seconds
    
    def on_for_rotations(self, speed, rotations, **kwargs):
        if rotations < 0:
            speed *= -1
            rotations *= -1
        self.on_for_seconds(speed, rotations / self.ROTATIONS_PER_SECOND_AT_MAX * abs(speed) / 100, **kwargs)

    def on_for_degrees(self, speed, degrees, **kwargs):
        self.on_for_rotations(speed, degrees / 360)

    def off(self):
        self.applied_force = 0

    