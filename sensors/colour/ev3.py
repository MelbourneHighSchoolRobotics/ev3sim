import random
from sensors.base import Sensor, ISensorInteractor
from sensors.colour.base import ColourSensorMixin
from visual.manager import ScreenObjectManager
from visual.utils import worldspace_to_screenspace

class ColorInteractor(ISensorInteractor):
    
    def tick(self, tick):
        super().tick(tick)
        try:
            self.sensor_class.calc_raw()
            self.object_map['light_up'].visual.fill = self.sensor_class.rgb()
        except:
            pass
        return False

class ColorSensor(Sensor, ColourSensorMixin):

    _r_calibration_max = 300
    _g_calibration_max = 300
    _b_calibration_max = 300

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Biases should be somewhere between 250/255 and 400/255.
        self.__r_bias = random.random()*150/255 + 250/255
        self.__g_bias = random.random()*150/255 + 250/255
        self.__b_bias = random.random()*150/255 + 250/255

    def raw(self):
        return self.saved_raw

    def calc_raw(self):
        res = self._SenseValueAboutPosition(self.global_position, lambda pos: ScreenObjectManager.instance.colourAtPixel(worldspace_to_screenspace(pos)))
        # These are 0-255. RAW is meant to be 0-1020 but actually more like 0-300.
        self.saved_raw = [
            res[0] * self.__r_bias, 
            res[1] * self.__g_bias, 
            res[2] * self.__b_bias,
        ]
    
    def calibrate_white(self):
        self._r_calibration_max, self._g_calibration_max, self._b_calibration_max = self.raw()
    
    def rgb(self):
        res = self.raw()
        return [
            min(max(res[0] * 255 / self._r_calibration_max, 0), 255),
            min(max(res[1] * 255 / self._g_calibration_max, 0), 255),
            min(max(res[2] * 255 / self._b_calibration_max, 0), 255),
        ]
    
    def reflected_light_intensity(self):
        raise NotImplementedError("`reflected_light_intensity` is currently not implemented.")