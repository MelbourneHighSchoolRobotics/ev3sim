import numpy as np
from objects.base import objectFactory
from sensors.base import Sensor, ISensorInteractor
from sensors.ultrasonic.base import UltrasonicSensorMixin
from simulation.loader import ScriptLoader
from visual.manager import ScreenObjectManager

class UltrasonicInteractor(ISensorInteractor):

    UPDATE_PER_SECOND = 20
    DRAW_RAYCAST = False

    def startUp(self):
        super().startUp()
        if self.DRAW_RAYCAST:
            from visual.objects import Line
            self.raycast_line = Line(
                start=self.object_map['light_up'].position,
                end=self.object_map['light_up'].position,
                fill='#ff0000',
            )
            key = self.object_map['light_up'].key + '_US_RAYCAST'
            ScreenObjectManager.instance.registerVisual(self.raycast_line, key)


    def tick(self, tick):
        if tick % (ScriptLoader.instance.GAME_TICK_RATE // self.UPDATE_PER_SECOND) == 0:
            self.sensor_class.calc()
            self.object_map['light_up'].visual.fill = (
                min(max((self.sensor_class.MAX_RAYCAST - self.sensor_class.distance_centimeters) * 255 / self.sensor_class.MAX_RAYCAST, 0), 255),
                0,
                0,
            )
            if self.DRAW_RAYCAST:
                obj = self.sensor_class._GenerateRaycast(self.sensor_class.global_position, self.sensor_class.parent.rotation + self.sensor_class.relativeRot, self.sensor_class.distance_centimeters).visual
                self.raycast_line.start = self.sensor_class.global_position
                self.raycast_line.end = self.sensor_class.global_position + self.sensor_class.distance_centimeters * np.array([np.cos(self.sensor_class.parent.rotation + self.sensor_class.relativeRot), np.sin(self.sensor_class.parent.rotation + self.sensor_class.relativeRot)])
        return False

class UltrasonicSensor(Sensor, UltrasonicSensorMixin):

    def __init__(self, parent, relativePos, relativeRot, **kwargs):
        super().__init__(parent, relativePos, relativeRot, **kwargs)
        self._SetIgnoredObjects([parent])
        self._InitialiseRaycast()

    def calc(self):
        self.saved = self._DistanceFromSensor(self.global_position, self.parent.rotation + self.relativeRot)
    
    @property
    def distance_centimeters(self):
        return self.saved
    
    @property
    def distance_inches(self):
        raise NotImplementedError("`distance_inches` is currently not implemented.")