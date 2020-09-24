class ButtonMixin:

    device_type = "brick_button"

    pressed = False

    def _getObjName(self, port):
        return "button" + port

    def generateBias(self):
        pass

    def toObject(self):
        data = {
            "address": self._interactor.port,
            "driver_name": "ev3sim-button",
            "pressed": int(self.pressed),
        }
        return data
