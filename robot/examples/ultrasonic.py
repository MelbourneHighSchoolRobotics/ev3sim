from robot import Robot
from devices.motor.ev3 import LargeMotor
from devices.ultrasonic.ev3 import UltrasonicSensor

class UltrasonicExample(Robot):

    def startUp(self):
        self.leftMotor : LargeMotor = self.getDevice('outB')
        self.rightMotor : LargeMotor = self.getDevice('outC')
        self.ultrasonic : UltrasonicSensor = self.getDevice('in3')
    
    def validateSpeed(self, speed):
        return max(min(speed, 100), -100)

    def tick(self, _):
        self.leftMotor.on(self.validateSpeed(3*(self.ultrasonic.distance_centimeters - 30)))
        self.rightMotor.on(self.validateSpeed(3*(self.ultrasonic.distance_centimeters - 30)))
