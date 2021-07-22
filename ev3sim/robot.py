import numpy as np
from ev3sim.file_helper import find_abs
from ev3sim.search_locations import code_locations
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import stop_on_pause
from ev3sim.simulation.randomisation import Randomiser


def add_devices(parent, device_info):
    devices = []
    for info in device_info:
        key = list(info.keys())[0]
        devices.append({"name": key})
        devices[-1].update(info[key])
        devices[-1]["type"] = "device"
    parent["children"] = parent.get("children", []) + devices


def add_to_key(obj, prefix):
    if isinstance(obj, dict):
        if "key" in obj:
            obj["key"] = prefix + obj["key"]
        for value in obj.values():
            add_to_key(value, prefix)
    if isinstance(obj, (list, tuple)):
        for v in obj:
            add_to_key(v, prefix)


def add_to_zpos(obj, amount):
    if isinstance(obj, dict):
        if "zPos" in obj:
            obj["zPos"] += amount
        for value in obj.values():
            add_to_zpos(value, amount)
    if isinstance(obj, (list, tuple)):
        for v in obj:
            add_to_zpos(v, amount)


def initialise_bot(topLevelConfig, robotFolder, prefix, path_index):
    # Returns the robot class, as well as a completed robot to add to the elements list.
    import yaml
    from os.path import join

    with open(join(robotFolder, "config.bot"), "r") as f:
        try:
            config = yaml.safe_load(f)
            mname, cname = config.get("robot_class", "ev3sim.robot.Robot").rsplit(".", 1)
            import importlib

            klass = getattr(importlib.import_module(mname), cname)
            bot_config = config["base_plate"]
            bot_config["type"] = "object"
            bot_config["physics"] = True
            add_devices(bot_config, config.get("devices", []))
            add_to_key(bot_config, prefix)
            add_to_zpos(bot_config, 10)
            # Append bot object to elements.
            topLevelConfig["elements"] = topLevelConfig.get("elements", []) + [bot_config]
            robot = klass()
            ScriptLoader.instance.addActiveScript(
                RobotInteractor(
                    **{
                        "robot": robot,
                        "base_key": bot_config["key"],
                        "path_index": path_index,
                        # Don't include directories here, since that shouldn't affect randomisation.
                        "filename": robotFolder.replace("\\", "/").rsplit("/", 1)[-1],
                    }
                )
            )
            robot.ID = prefix
            robot._follow_collider_offset = config.get("follow_collider", [0, 0])
            ScriptLoader.instance.robots[prefix] = robot
            ScriptLoader.instance.outstanding_events[prefix] = []
            if config.get("type", "python") == "mindstorms":
                scriptname = config.get("script", "program.ev3")
            else:
                scriptname = config.get("script", "code.py")
            if scriptname is not None:
                scriptname = find_abs(scriptname, code_locations(robotFolder))
            ScriptLoader.instance.scriptnames[prefix] = scriptname

        except yaml.YAMLError as exc:
            print(f"An error occurred while loading robot preset {robotFolder}. Exited with error: {exc}")


class RobotInteractor(IInteractor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.robot_class: Robot = kwargs.get("robot")
        self.robot_class._interactor = self
        self.robot_key = kwargs.get("base_key")
        self.path_index = kwargs.get("path_index")
        self.filename = kwargs.get("filename")

    def connectDevices(self):
        self.devices = {}
        for interactor in getattr(ScriptLoader.instance.object_map[self.robot_key], "device_interactors", []):
            self.devices[interactor.port] = interactor.device_class
            interactor.port_key = f"{self.filename}-{self.path_index}-{interactor.port}"
            Randomiser.createPortRandomiserWithSeed(interactor.port_key)
        ScriptLoader.instance.object_map[self.robot_key].robot_class = self.robot_class

    def initialiseDevices(self):
        for interactor in getattr(ScriptLoader.instance.object_map[self.robot_key], "device_interactors", []):
            interactor.device_class.generateBias()

    def startUp(self):
        self.robot_class.startUp()

    @stop_on_pause
    def tick(self, tick):
        self.robot_class.tick(tick)
        return False

    def handleEvent(self, event):
        self.robot_class.handleEvent(event)

    def collectDeviceData(self):
        res = {}
        for port, device in self.devices.items():
            if device.device_type not in res:
                res[device.device_type] = {}
            try:
                res[device.device_type][device._getObjName(port)] = device.toObject()
            except Exception as e:
                # Something has failed, so let the attached script know.
                return str(e)
        return res

    def resetBot(self):
        ScriptLoader.instance.object_map[self.robot_key].body.velocity = (0, 0)
        ScriptLoader.instance.object_map[self.robot_key].body.angular_velocity = 0
        for dev in getattr(self, "devices", {}).values():
            dev.reset()


class Robot:
    """
    A robot is as you'd expect in the physical sense - a collection of devices on a base board,
    with it's own internal logic and events.

    This class however does not contain the physical definition of the robot though, just the brains.

    All robot 'definitions' (see `examples/robots/controllable.bot`) reference a `class_path` (Which is by default this base class), and the actions of this bot are defined by how the following functions are modified:
    """

    spawned = False

    def getDevice(self, port):
        """
        Returns an instance of the device on the port specified.

        :param string port: The port of the device to retrieve.

        Example usage:
        ```
        >>> leftMotor = self.getDevice('outB')
        ```
        """
        try:
            return self._interactor.devices[port]
        except:
            raise ValueError(f"No device on port {port} found.")

    def getDeviceFromPath(self, device_class, device_name):
        for port, dev in self._interactor.devices.items():
            if dev.device_type == device_class and dev._getObjName(port) == device_name:
                return dev
        raise ValueError(f"No device found with path {device_class} {device_name}")

    def startUp(self):
        """
        Override with code to be executed whenever the robot is instantiated.
        """
        pass

    def onSpawn(self):
        """
        Since soccer and possibly other games require the placement and rotation of bots, a method separate to ``startUp``
        exists for code to execute once this placement is complete.

        As an example, calibrating the compass sensors should be done ``onSpawn``, rather than on ``startUp``.
        """
        self.spawned = True
        self._interactor.initialiseDevices()

    def tick(self, tick):
        """
        Override with code to be executed once every simulation tick.

        :param int tick: The tick since beginning of simulation.
        """
        pass

    def handleEvent(self, event):
        """
        Override with code to be executed for every `pygame.event.EventType` (https://www.pygame.org/docs/ref/event.html).

        :param pygame.event.Event event: The pygame event registered.

        Shouldn't be required for normal bots.
        """
        pass


class AngleSnapRobot(Robot):

    # This isn't very lenient, you still need to do most of the work.
    SNAP_ANGLES = [0, np.pi / 2, np.pi, 3 * np.pi / 2]
    ANGLE_CUTOFF = np.pi / 24
    VELOCITY_CUTOFF = 0.2

    def tick(self, tick):
        super().tick(tick)
        if self._interactor.robot_key in ScriptLoader.instance.object_map:
            obj = ScriptLoader.instance.object_map[self._interactor.robot_key]
            rot = obj.body.angle
            if abs(obj.body.angular_velocity) < self.VELOCITY_CUTOFF:
                for angle in self.SNAP_ANGLES:
                    diff = rot - angle
                    while diff >= np.pi:
                        diff -= 2 * np.pi
                    while diff < -np.pi:
                        diff += 2 * np.pi
                    if abs(diff) < self.ANGLE_CUTOFF:
                        obj.body.angle = angle
                        # Don't reset angular velocity, then we can't move.


from ev3sim.visual.settings.elements import TextEntry

visual_settings = [
    {"height": lambda s: 90, "objects": [TextEntry("__filename__", "BOT NAME", None, (lambda s: (0, 20)))]},
]
