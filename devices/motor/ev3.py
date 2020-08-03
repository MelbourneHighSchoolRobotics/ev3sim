import pygame
import numpy as np
from devices.base import Device, IDeviceInteractor
from devices.motor.base import MotorMixin
from objects.utils import local_space_to_world_space
from simulation.loader import ScriptLoader
from visual.manager import ScreenObjectManager
from visual.objects import visualFactory

class MotorInteractor(IDeviceInteractor):

    @property
    def name(self):
        if isinstance(self.device_class, LargeMotor):
            return 'LMotor'
        return 'MMotor'

    def tick(self, tick):
        self.device_class._updateTime(tick)
        if self.device_class.applied_force > 0:
            ScriptLoader.instance.object_map[self.getPrefix() + 'light_up'].visual.fill = (0, 255 * self.device_class.applied_force / self.device_class.MAX_FORCE, 0)
        else:
            ScriptLoader.instance.object_map[self.getPrefix() + 'light_up'].visual.fill = (- 255 * self.device_class.applied_force / self.device_class.MAX_FORCE, 0, 0)
        self.device_class._applyMotors(self.physical_object, self.relative_location, self.relative_rotation)
        return False

class LargeMotor(Device, MotorMixin):

    MAX_FORCE = 1000

class MediumMotor(Device, MotorMixin):

    MAX_FORCE = 500