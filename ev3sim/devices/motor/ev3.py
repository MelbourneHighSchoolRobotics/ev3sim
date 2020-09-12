import pygame
import numpy as np
from ev3sim.devices.base import Device, IDeviceInteractor
from ev3sim.devices.motor.base import MotorMixin
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.objects import visualFactory


class MotorInteractor(IDeviceInteractor):
    @property
    def name(self):
        if isinstance(self.device_class, LargeMotor):
            return "LMotor"
        return "MMotor"

    def tick(self, tick):
        self.device_class._updateTime(tick)
        if self.device_class.applied_force > 0:
            ScriptLoader.instance.object_map[self.getPrefix() + "light_up"].visual.fill = (
                0,
                255 * self.device_class.applied_force / self.device_class.MAX_FORCE,
                0,
            )
        else:
            ScriptLoader.instance.object_map[self.getPrefix() + "light_up"].visual.fill = (
                -255 * self.device_class.applied_force / self.device_class.MAX_FORCE,
                0,
                0,
            )
        self.device_class._applyMotors(self.physical_object, self.relative_location, self.relative_rotation)
        return False


class LargeMotor(MotorMixin, Device):

    driver_name = "lego-ev3-l-motor"
    THEORETICAL_MAX_FORCE = 1000
    ROTATIONS_PER_SECOND_AT_MAX = 10


class MediumMotor(MotorMixin, Device):

    driver_name = "lego-ev3-m-motor"
    THEORETICAL_MAX_FORCE = 500
    ROTATIONS_PER_SECOND_AT_MAX = 5
