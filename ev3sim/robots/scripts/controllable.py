import pygame
import numpy as np
from ev3sim.robot import Robot
from ev3sim.devices.motor.ev3 import LargeMotor
from ev3sim.devices.compass.ev3 import CompassSensor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.visual.utils import hsl_to_rgb

class ControllableBot(Robot):

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.direction[1] += 1
            elif event.key == pygame.K_DOWN:
                self.direction[1] -= 1
            elif event.key == pygame.K_LEFT:
                self.direction[0] -= 1
            elif event.key == pygame.K_RIGHT:
                self.direction[0] += 1
            elif event.key == pygame.K_r:
                self.rotate = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                self.direction[1] -= 1
            elif event.key == pygame.K_DOWN:
                self.direction[1] += 1
            elif event.key == pygame.K_LEFT:
                self.direction[0] += 1
            elif event.key == pygame.K_RIGHT:
                self.direction[0] -= 1
            elif event.key == pygame.K_r:
                self.rotate = False

    def startUp(self):
        self.direction = np.array([0.0, 0.0])
        self.rotate = False
        self.leftMotor : LargeMotor = self.getDevice('outB')
        self.rightMotor : LargeMotor = self.getDevice('outC')
        self.topMotor : LargeMotor = self.getDevice('outA')
        self.botMotor : LargeMotor = self.getDevice('outD')
        self.compass : CompassSensor = self.getDevice('in4')

    def onSpawn(self):
        self.compass.calibrate()

    def tick(self, tick):
        # hue = (tick % 120) * 3
        # r, g, b = hsl_to_rgb(hue, 1, 0.5)
        # ScriptLoader.instance.object_map[self._interactor.robot_key].children[0].visual.fill = (r*255, g*255, b*255, 0.1)
        if self.rotate:
            self.rotate_anticlockwise()
            return
        if self.direction[0] == self.direction[1] and self.direction[0] == 0:
            self.move_global_rotation(0, speed=0)
        else:
            rot = np.arctan2(self.direction[1], self.direction[0])
            self.move_global_rotation(rot)

    def rotate_anticlockwise(self, speed=100):
        self.leftMotor.on(-speed)
        self.rightMotor.on(speed)
        self.topMotor.on(speed)
        self.botMotor.on(-speed)

    def move_relative_rotation(self, bearing, speed=100):
        hMotorScale = np.sin(bearing)
        vMotorScale = np.cos(bearing)
        self.leftMotor.on(vMotorScale * speed)
        self.rightMotor.on(vMotorScale * speed)
        self.topMotor.on(hMotorScale * speed)
        self.botMotor.on(hMotorScale * speed)
    
    def move_global_rotation(self, bearing, speed=100):
        self.move_relative_rotation(bearing - np.pi * self.compass.value() / 180, speed=speed)
