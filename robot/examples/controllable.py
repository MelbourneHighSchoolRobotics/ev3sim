import pygame
import numpy as np
from robot import Robot
from devices.motor.ev3 import LargeMotor
from devices.ultrasonic.ev3 import UltrasonicSensor

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
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                self.direction[1] -= 1
            elif event.key == pygame.K_DOWN:
                self.direction[1] += 1
            elif event.key == pygame.K_LEFT:
                self.direction[0] += 1
            elif event.key == pygame.K_RIGHT:
                self.direction[0] -= 1

    def startUp(self):
        self.direction = np.array([0.0, 0.0])
        self.leftMotor : LargeMotor = self.getDevice('outB')
        self.rightMotor : LargeMotor = self.getDevice('outC')
        self.topMotor : LargeMotor = self.getDevice('outA')
        self.botMotor : LargeMotor = self.getDevice('outD')
        self.compass : CompassSensor = self.getDevice('in4')

    def tick(self, tick):
        if self.direction[0] == self.direction[1] and self.direction[0] == 0:
            self.move_global_rotation(0, speed=0)
        else:
            rot = np.arctan2(self.direction[1], self.direction[0])
            self.move_global_rotation(rot)

    def move_relative_rotation(self, bearing, speed=100):
        hMotorScale = np.sin(bearing)
        vMotorScale = np.cos(bearing)
        self.leftMotor.on(vMotorScale * speed)
        self.rightMotor.on(vMotorScale * speed)
        self.topMotor.on(hMotorScale * speed)
        self.botMotor.on(hMotorScale * speed)
    
    def move_global_rotation(self, bearing, speed=100):
        self.move_relative_rotation(bearing - np.pi * self.compass.value() / 180, speed=speed)
