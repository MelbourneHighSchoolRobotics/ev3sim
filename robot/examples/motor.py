import noise
from robot import Robot
from devices.motor.ev3 import LargeMotor
from devices.ultrasonic.ev3 import UltrasonicSensor

class MotorBot(Robot):

    # Perlin noise sample - see https://medium.com/@yvanscher/playing-with-perlin-noise-generating-realistic-archipelagos-b59f004d8401
    noise_scale = 100
    noise_octaves = 6
    noise_lacunarity = 2.0
    noise_persistence = 0.5

    def startUp(self):
        self.leftMotor : LargeMotor = self.getDevice('outB')
        self.rightMotor : LargeMotor = self.getDevice('outC')

    def tick(self, tick):
        lSpeed = 100 * noise.pnoise1(tick / self.noise_scale, octaves=self.noise_octaves, persistence=self.noise_persistence, lacunarity=self.noise_lacunarity, base=0)
        rSpeed = 100 * noise.pnoise1(-tick / self.noise_scale, octaves=self.noise_octaves, persistence=self.noise_persistence, lacunarity=self.noise_lacunarity, base=0)
        self.leftMotor.on(lSpeed)
        self.rightMotor.on(rSpeed)
