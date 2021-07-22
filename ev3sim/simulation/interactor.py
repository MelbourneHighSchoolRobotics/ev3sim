from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.file_helper import find_abs
from ev3sim.settings import SettingsManager
from ev3sim.search_locations import preset_locations


class IInteractor:
    """
    An interactor can be thought of as a robot in the simulation which has much more access to the inner workings of the system, and no physical presence.

    Any actions or dynamic elements in the soccer simulation is due to `interactors`. You can find the location of these interactors in `presets/soccer.yaml`.
    """

    # This defines the ordering of this interactor in the list of total interactors, affecting the order in which `afterPhysics` and `tick` are called.
    SORT_ORDER = 0

    constants: dict

    AUTOSTART_BOTS = False

    def __init__(self, **kwargs):
        pass

    def startUp(self):
        """Called when the interactor is instantiated (After elements are spawned in, but before any ticks are done)."""
        self.locateBots()
        for robot in self.robots:
            robot.robot_class.onSpawn()
        if self.AUTOSTART_BOTS:
            self.restartBots()

    def tick(self, tick) -> bool:
        """
        Called once every tick in the simulation.

        :param int tick: The number of ticks since epoch.

        :returns bool: If ``True`` is returned, this interactor is assumed to be complete, and will be killed off at the end of the tick.
        """
        return False

    def afterPhysics(self):
        """
        Called once every tick in the simulation, *after* physics has been applied.
        """
        pass

    def tearDown(self):
        """Called before the interactor is killed, so that it can do any cleanup necessary."""
        pass

    def handleEvent(self, event):
        """
        Override with code to be executed for every `pygame.event.EventType` (https://www.pygame.org/docs/ref/event.html).

        :param pygame.event.Event event: The pygame event registered.
        """
        pass

    # Some helper functions
    def locateBots(self):
        """Identifies all spawned robots."""
        from ev3sim.simulation.loader import ScriptLoader

        self.robots = []
        bot_index = 0
        while True:
            # Find the next robot.
            possible_keys = []
            for key in ScriptLoader.instance.object_map.keys():
                if key.startswith(f"Robot-{bot_index}"):
                    possible_keys.append(key)
            if len(possible_keys) == 0:
                break
            possible_keys.sort(key=len)
            self.robots.append(ScriptLoader.instance.object_map[possible_keys[0]])
            bot_index += 1

        if len(self.robots) == 0:
            raise ValueError("No robots loaded.")

    def killBots(self):
        """Kill all ongoing robot scripts."""
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.killAllProcesses()

    def restartBots(self):
        """Kill all ongoing robot scripts and start them again"""
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.events import GAME_RESET

        for robotID in ScriptLoader.instance.robots.keys():
            # Restart the robot scripts.
            if hasattr(ScriptLoader.instance.robots[robotID], "_interactor"):
                ScriptLoader.instance.robots[robotID]._interactor.resetBot()
            ScriptLoader.instance.startProcess(robotID, kill_recent=True)
            ScriptLoader.instance.sendEvent(robotID, GAME_RESET, {})

        # Remove all requested input from robots
        to_remove = []
        for i, output in enumerate(ScriptLoader.instance.input_requests):
            if not isinstance(output, IInteractor):
                to_remove.append(i)
        for i in to_remove[::-1]:
            del ScriptLoader.instance.input_requests[i]
        sim = ScreenObjectManager.instance.screens[ScreenObjectManager.instance.SCREEN_SIM]
        to_remove = []
        for i, message in enumerate(sim.messages):
            if isinstance(message[1], str) and message[1].startswith("input_Robot-"):
                to_remove.append(i)
            elif not (isinstance(message[1], str) and message[1].startswith("input")):
                # Also remove any other messages that are not system input requests.
                to_remove.append(i)
        for i in to_remove[::-1]:
            del sim.messages[i]
        ScreenObjectManager.instance.screens[ScreenObjectManager.instance.SCREEN_SIM].regenerateObjects()

    def handleInput(self, msg):
        pass


class PygameGuiInteractor(BaseMenu, IInteractor):
    def __init__(self, **kwargs):
        """Fix to avoid size not being set correctly."""
        from ev3sim.visual.manager import ScreenObjectManager

        IInteractor.__init__(self, **kwargs)
        BaseMenu.__init__(self, (ScreenObjectManager.instance.SCREEN_WIDTH, ScreenObjectManager.instance.SCREEN_HEIGHT))


def fromOptions(options):
    if "filename" in options:
        import yaml

        fname = find_abs(options["filename"])
        with open(fname, "r") as f:
            config = yaml.safe_load(f)
            return fromOptions(config)
    if "class_path" not in options:
        raise ValueError(
            "Your options has no 'class_path' or 'filename' entry (Or the file you reference has no 'class_path' entry')"
        )
    import importlib

    if isinstance(options["class_path"], str):
        mname, cname = options["class_path"].rsplit(".", 1)

        klass = getattr(importlib.import_module(mname), cname)
    else:
        from importlib.machinery import SourceFileLoader

        module = SourceFileLoader("not_main", find_abs(options["class_path"][0], preset_locations())).load_module()
        klass = getattr(module, options["class_path"][1])
    topObj = klass(*options.get("args", []), **options.get("kwargs", {}))
    # Add any settings for this interactor, if applicable.
    # This only works for package presets. Not workspace ones.
    if "settings_name" in options:
        name = options["settings_name"]
        if "settings_defn" not in options:
            raise ValueError(f"Expected a settings object to add with group name {name}")
        mname, cname = options["settings_defn"].rsplit(".", 1)
        obj = getattr(importlib.import_module(mname), cname)
        SettingsManager.instance.addSettingGroup(name, obj)
        # We need to remove this setting once the simulation ends, so save the name.
        topObj._settings_name = name
    return topObj
