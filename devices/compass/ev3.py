import numpy as np
from devices.base import IDeviceInteractor, Device
from devices.compass.base import CompassSensorMixin
from objects.utils import local_space_to_world_space
from simulation.loader import ScriptLoader

class CompassInteractor(IDeviceInteractor):

    name = 'COMPASS'

    def tick(self, tick):
        self.device_class.calc()
        self.do_rotation = self.device_class.value() * np.pi / 180
    
    def afterPhysics(self):
        for i, obj in enumerate(self.generated):
            obj.position = local_space_to_world_space(
                self.relative_location + local_space_to_world_space(self.relative_positions[i], self.relative_rotation, np.array([0 ,0])), 
                self.physical_object.rotation, 
                self.physical_object.position,
            )
            if obj.key == (self.getPrefix() + 'relative_north'):
                obj.rotation = self.device_class.global_rotation - self.do_rotation
            else:
                obj.rotation = self.physical_object.rotation + self.relative_rotation

class CompassSensor(Device, CompassSensorMixin):

    def calc(self):
        self._value = self._getValue()

    def value(self):
        return self._value

    def calibrate(self):
        self._setRelative()