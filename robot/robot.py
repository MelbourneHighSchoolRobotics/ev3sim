from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from simulation.world import stop_on_pause

def add_devices(parent, device_info):
    devices = []
    for info in device_info:
        key = list(info.keys())[0]
        devices.append({"name":key})
        devices[-1].update(info[key])
        devices[-1]["type"] = "device"
    parent["children"] = parent.get("children", []) + devices

def add_to_key(obj, prefix):
    if isinstance(obj, dict):
        if 'key' in obj:
            obj['key'] = prefix + obj['key']
        for value in obj.values():
            add_to_key(value, prefix)
    if isinstance(obj, (list, tuple)):
        for v in obj:
            add_to_key(v, prefix)

def initialise_bot(topLevelConfig, filename, prefix):
    # Returns the robot class, as well as a completed robot to add to the elements list.
    import yaml
    with open(filename, 'r') as f:
        try:
            config = yaml.safe_load(f)
            if 'robot_class' not in config:
                raise ValueError("Your robot preset has no 'robot_class' or 'filename' entry (Or the file you reference has no 'robot_class' entry')")
            mname, cname = config['robot_class'].rsplit('.', 1)
            import importlib
            klass = getattr(importlib.import_module(mname), cname)
            bot_config = config['base_plate']
            bot_config['type'] = 'object'
            bot_config['physics'] = True
            add_devices(bot_config, config.get('devices', []))
            add_to_key(bot_config, prefix)
            # Append bot object to elements.
            topLevelConfig['elements'] = topLevelConfig.get('elements', []) + [bot_config]
            robot = klass()
            ScriptLoader.instance.active_scripts.append(RobotInteractor(**{
                'robot': robot,
                'base_key': bot_config['key']
            }))
        except yaml.YAMLError as exc:
            print(f"An error occured while loading robot preset {filename}. Exited with error: {exc}")

class RobotInteractor(IInteractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.robot_class : Robot = kwargs.get('robot')
        self.robot_class._interactor = self
        self.robot_key = kwargs.get('base_key')
    
    def connectDevices(self):
        self.devices = {}
        for interactor in ScriptLoader.instance.object_map[self.robot_key].device_interactors:
            self.devices[interactor.port] = interactor.device_class
        ScriptLoader.instance.object_map[self.robot_key].robot_class = self.robot_class

    def startUp(self):
        self.robot_class.startUp()

    @stop_on_pause
    def tick(self, tick):
        self.robot_class.tick(tick)
        return False
    
    def handleEvent(self, event):
        self.robot_class.handleEvent(event)

class Robot:
    """
    A robot is as you'd expect in the physical sense - a collection of devices on a base board,
    with it's own internal logic and events.

    This class however does not contain the physical definition of the robot though, just the brains.

    All robot 'definitions' (see `robot/examples/controllable.yaml`) must reference the class path of some object implementing the below methods.
    """

    def getDevice(self, port):
        """
        Returns an instance of the device on the port specified.
        
        Example usage:
        ```
        >>> leftMotor = self.getDevice('outB')
        ```
        """
        try:
            return self._interactor.devices[port]
        except:
            raise ValueError(f"No device on port {port} found.")

    def startUp(self):
        """
        Override with code to be executed whenever the robot is instantiated.
        """
        pass
    
    def onSpawn(self):
        """
        Since soccer and possibly other games require the placement and rotation of bots, a method separate to `startUp`
        exists for code to execute once this placement is complete.

        As an example, calibrating the compass sensors should be done `onSpawn`, rather than on `startUp`.
        """
        pass

    def tick(self, tick):
        """
        Override with code to be executed once every simulation tick.

        :param int tick: The tick since beginning of simulation.
        """
        pass

    def handleEvent(self, event):
        """
        Override with code to be executed for every `pygame.event.EventType` (https://www.pygame.org/docs/ref/event.html).

        Shouldn't be required for normal bots.
        """
        pass