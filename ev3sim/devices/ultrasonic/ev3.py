import numpy as np
from ev3sim.objects.base import objectFactory
from ev3sim.devices.base import Device, IDeviceInteractor
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.devices.ultrasonic.base import UltrasonicSensorMixin
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.visual.manager import ScreenObjectManager

class UltrasonicInteractor(IDeviceInteractor):

    UPDATE_PER_SECOND = 5

    def tick(self, tick):
        if tick % (ScriptLoader.instance.GAME_TICK_RATE // self.UPDATE_PER_SECOND) == 0:
            self.device_class._calc()
            ScriptLoader.instance.object_map[self.getPrefix() + 'light_up'].visual.fill = (
                min(max((self.device_class.MAX_RAYCAST - self.device_class.distance_centimeters) * 255 / self.device_class.MAX_RAYCAST, 0), 255),
                0,
                0,
            )
        return False

class UltrasonicSensor(UltrasonicSensorMixin, Device):
    """
    Ultrasonic sensor, reads the distance between the sensor and the closest physics object (directly in front of the sensor).

    This measurement is done from the light on the sensor, so a reading of 5cm means the closest object is 5cm away from the light.
    """

    name = 'Ultrasonic'

    def __init__(self, parent, relativePos, relativeRot, **kwargs):
        super().__init__(parent, relativePos, relativeRot, **kwargs)
        self._SetIgnoredObjects([parent])

    def _calc(self):
        self.saved = self._DistanceFromSensor(ScriptLoader.instance.object_map[self._interactor.getPrefix() + 'light_up'].position, self.parent.rotation + self.relativeRot)
    
    @property
    def distance_centimeters(self):
        """
        Get the distance between the ultrasonic sensor and the object, in centimeters.
        """
        return int(self.saved)
    
    @property
    def distance_inches(self):
        """
        Get the distance between the ultrasonic sensor and the object, in inches.
        """
        return int(self.distance_centimeters * 0.3937008)