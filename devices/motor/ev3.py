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

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == self.device_class.F_k:
                self.device_class.on(100)
            if event.key == self.device_class.B_k:
                self.device_class.on(-100)
        if event.type == pygame.KEYUP:
            if event.key == self.device_class.F_k and self.device_class.applied_force > 0:
                self.device_class.off()
            if event.key == self.device_class.B_k and self.device_class.applied_force < 0:
                self.device_class.off()

    def tick(self, tick):
        self.device_class._updateTime(tick)
        if self.device_class.applied_force > 0:
            ScriptLoader.instance.object_map[self.getPrefix() + 'light_up'].visual.fill = (0, 255 * self.device_class.applied_force / self.device_class.MAX_FORCE, 0)
        else:
            ScriptLoader.instance.object_map[self.getPrefix() + 'light_up'].visual.fill = (- 255 * self.device_class.applied_force / self.device_class.MAX_FORCE, 0, 0)
        self.device_class._applyMotors(self.physical_object, local_space_to_world_space(self.relative_location, self.physical_object.rotation, np.array([0, 0])), self.relative_rotation + self.physical_object.rotation)
        return False

class LargeMotor(Device, MotorMixin):

    MAX_FORCE = 100000
    F_k = pygame.K_f
    B_k = pygame.K_v

class MediumMotor(Device, MotorMixin):

    MAX_FORCE = 50000
    F_k = pygame.K_j
    B_k = pygame.K_n