import yaml
import numpy as np
import ev3sim.visual.utils as utils
from ev3sim.simulation.interactor import IInteractor, fromOptions
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.objects.base import objectFactory
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.file_helper import find_abs


class Device:

    device_type = "CHANGE_ME"

    def __init__(self, parent, relativePos, relativeRot):
        # parent is the physics object containing this device.
        # visual is the object representing the device
        self.parent = parent
        self.relativePos = relativePos
        self.relativeRot = relativeRot

    @property
    def global_position(self):
        return self.parent.position + np.array(
            [
                self.relativePos[0] * np.cos(self.parent.rotation) - self.relativePos[1] * np.sin(self.parent.rotation),
                self.relativePos[1] * np.cos(self.parent.rotation) + self.relativePos[0] * np.sin(self.parent.rotation),
            ]
        )

    @property
    def global_rotation(self):
        return self.parent.rotation + self.relativeRot

    def toObject(self):
        raise NotImplementedError("Implement the toObject method.")

    def applyWrite(self, attribute, value):
        raise NotImplementedError("Implement the applyWrite method.")

    def _getObjName(self, port):
        return port


class IDeviceInteractor(IInteractor):

    # Device Interactor goes before robot class to precalc.
    SORT_ORDER = -5

    name = "UNNAMED"

    port_key = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_class = kwargs.get("device")
        self.device_class._interactor = self
        self.physical_object = kwargs.get("parent")
        self.relative_location = kwargs.get("relative_location")
        self.relative_rotation = kwargs.get("relative_rotation")
        i1, i2 = kwargs.get("device_index"), kwargs.get("single_device_index")
        self.index = f"{i1}-{i2}"
        self.items = kwargs.get("elements", [])
        self.port = kwargs.get("port")

    def getPrefix(self):
        return f"{self.physical_object.key}-{self.name}-{self.index}-"

    def startUp(self):
        self.relative_positions = []
        for x in range(len(self.items)):
            self.items[x]["key"] = self.getPrefix() + self.items[x]["key"]
            self.items[x]["type"] = "object"
            if "visual" in self.items[x]:
                self.items[x]["visual"]["zPos"] = (
                    self.items[x]["visual"].get("zPos", 0) + self.physical_object.visual.zPos
                )
            self.relative_positions.append(self.items[x]["position"])
        self.generated = ScriptLoader.instance.loadElements(self.items)
        self.physical_object.children.extend(self.generated)

    def afterPhysics(self):
        from ev3sim.objects.base import PhysicsObject

        for i, obj in enumerate(self.generated):
            obj.position = local_space_to_world_space(
                self.relative_location
                + local_space_to_world_space(self.relative_positions[i], self.relative_rotation, np.array([0, 0])),
                self.physical_object.rotation,
                self.physical_object.position,
            )
            obj.rotation = self.physical_object.rotation + self.relative_rotation
            if isinstance(obj, PhysicsObject):
                obj.body.position = obj.position
                obj.body.angle = obj.rotation

    def random(self):
        return Randomiser.getPortRandom(self.port_key).random()


def initialise_device(deviceData, parentObj, index):
    classes = find_abs("devices/classes.yaml")
    devices = yaml.safe_load(open(classes, "r"))
    name = deviceData["name"]
    if name not in devices:
        raise ValueError(f"Unknown device type {name}")
    fname = find_abs(devices[name], allowed_areas=["local/devices/", "package/devices/"])
    with open(fname, "r") as f:
        try:
            config = yaml.safe_load(f)
            utils.GLOBAL_COLOURS.update(config.get("colours", {}))
            mname, cname = config["class"].rsplit(".", 1)
            import importlib

            klass = getattr(importlib.import_module(mname), cname)
            relative_location = deviceData.get("position", [0, 0])
            relative_rotation = deviceData.get("rotation", 0) * np.pi / 180
            device = klass(parentObj, relative_location, relative_rotation)
            for i, opt in enumerate(config.get("interactors", [])):
                res = opt.get("kwargs", {})
                res.update(
                    {
                        "device": device,
                        "parent": parentObj,
                        "relative_location": relative_location,
                        "relative_rotation": relative_rotation,
                        "device_index": index,
                        "single_device_index": i,
                        "port": deviceData["port"],
                    }
                )
                opt["kwargs"] = res
                interactor = fromOptions(opt)
                if not hasattr(parentObj, "device_interactors"):
                    parentObj.device_interactors = []
                parentObj.device_interactors.append(interactor)
                ScriptLoader.instance.addActiveScript(interactor)
        except yaml.YAMLError as exc:
            print(f"An error occurred while loading devices. Exited with error: {exc}")
