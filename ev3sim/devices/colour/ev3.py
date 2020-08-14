import random
from ev3sim.devices.base import Device, IDeviceInteractor
from ev3sim.devices.colour.base import ColourSensorMixin
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import worldspace_to_screenspace

class ColorInteractor(IDeviceInteractor):
    
    name = 'COLOUR'

    def tick(self, tick):
        try:
            self.device_class._calc_raw()
            ScriptLoader.instance.object_map[self.getPrefix() + 'light_up'].visual.fill = self.device_class.rgb()
        except:
            pass
        return False

class ColorSensor(ColourSensorMixin, Device):
    """
    EV3 Color Sensor.
    
    Makes available the red green and blue values viewed under the sensor.
    Note that this isn't exactly what's seen, you will likely get more 
    reasonable and reproduceable values by using the `calibrate_white` method.
    """

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
        """
        Raw sensor values.

        In order to scale these to what the sensor thinks is White, use `calibrate_white` and `rgb`.

        :returns: R, G, B values in a tuple (0-400ish)
        """
        return self.saved_raw

    def _calc_raw(self):
        res = self._SenseValueAboutPosition(self.global_position, lambda pos: ScreenObjectManager.instance.colourAtPixel(worldspace_to_screenspace(pos)))
        # These are 0-255. RAW is meant to be 0-1020 but actually more like 0-300.
        self.saved_raw = [
            int(res[0] * self.__r_bias), 
            int(res[1] * self.__g_bias), 
            int(res[2] * self.__b_bias),
        ]
    
    def calibrate_white(self):
        """
        Calibrates the current sensor reading to be the colour white.

        For example, if this is over a gray patch, then all new readings in rgb will be lighter than in actuality,
        and anything more 'white' than that gray spot will be RGB 255, 255, 255.
        """
        self._r_calibration_max, self._g_calibration_max, self._b_calibration_max = self.raw()
    
    def rgb(self):
        """
        Returns the scaled to bias RGB values.

        :returns: R, G, B values in a tuple (0 - 255).
        """
        res = self.raw()
        return [
            min(max(res[0] * 255 / self._r_calibration_max, 0), 255),
            min(max(res[1] * 255 / self._g_calibration_max, 0), 255),
            min(max(res[2] * 255 / self._b_calibration_max, 0), 255),
        ]
    
    def reflected_light_intensity(self):
        """Not implemented"""
        raise NotImplementedError("`reflected_light_intensity` is currently not implemented.")