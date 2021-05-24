from ev3sim.code_helpers import CommandSystem
from ev3sim.constants import EV3SIM_BOT_COMMAND
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.settings import BindableValue, ObjectSetting
from ev3sim.search_locations import theme_locations
import pygame
import pygame.freetype
import yaml
from typing import Dict, List, Tuple

import ev3sim.visual.utils as utils


class ScreenObjectManager:

    instance: "ScreenObjectManager"

    SCREEN_MENU = "MAIN_MENU"
    SCREEN_SIM = "SIMULATOR"
    SCREEN_BOTS = "BOT_SELECT"
    SCREEN_BATCH = "BATCH_SELECT"
    SCREEN_SETTINGS = "SETTINGS"
    SCREEN_UPDATE = "UPDATE"
    SCREEN_BOT_EDIT = "BOT_EDIT"
    SCREEN_RESCUE_EDIT = "RESCUE_EDIT"

    screen_stack = []

    screen: pygame.Surface
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 960
    MAP_WIDTH: float = 200
    MAP_HEIGHT: float = 200
    BACKGROUND_COLOUR = "#1f1f1f"

    _background_colour: Tuple[int]

    objects: Dict[str, "visual.objects.IVisualElement"]  # noqa: F821
    sorting_order: List[str]

    # This needs to be provided in settings.
    theme_path = ""

    def __init__(self, **kwargs):
        ScreenObjectManager.instance = self
        self.objects = {}
        self.sorting_order = []
        self.kill_keys = []
        self.screen_stack = []
        self.initFromKwargs(**kwargs)

    def resetVisualElements(self):
        self.sorting_order = []
        self.objects = {}
        self.kill_keys = []

    def initFromKwargs(self, **kwargs):
        self.original_SCREEN_WIDTH = self.SCREEN_WIDTH
        self.original_SCREEN_HEIGHT = self.SCREEN_HEIGHT
        self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL = self.SCREEN_WIDTH, self.SCREEN_HEIGHT
        self.background_colour = self.BACKGROUND_COLOUR
        self.unhandled_events = []

    @property
    def background_colour(self):
        return self._background_colour

    @background_colour.setter
    def background_colour(self, value):
        if isinstance(value, str):
            if value in utils.GLOBAL_COLOURS:
                value = utils.GLOBAL_COLOURS[value]
            if value.startswith("#"):
                value = value[1:]
            self._background_colour = utils.hex_to_pycolor(value)
        else:
            self._background_colour = value

    def initScreens(self):
        self.screens = {}
        # Update dialog
        from ev3sim.visual.menus.update_dialog import UpdateMenu

        self.screens[self.SCREEN_UPDATE] = UpdateMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Menu screen
        from ev3sim.visual.menus.main import MainMenu

        self.screens[self.SCREEN_MENU] = MainMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Bots screen
        from ev3sim.visual.menus.bot_menu import BotMenu

        self.screens[self.SCREEN_BOTS] = BotMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Bot edit screen
        from ev3sim.visual.menus.bot_edit import BotEditMenu

        self.screens[self.SCREEN_BOT_EDIT] = BotEditMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Batch screen
        from ev3sim.visual.menus.batch_select import BatchMenu

        self.screens[self.SCREEN_BATCH] = BatchMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Simulator screen
        from ev3sim.visual.menus.sim_menu import SimulatorMenu

        self.screens[self.SCREEN_SIM] = SimulatorMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Settings generic screen
        from ev3sim.visual.settings.menu import SettingsMenu

        self.screens[self.SCREEN_SETTINGS] = SettingsMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Rescue edit screen
        from ev3sim.visual.menus.rescue_edit import RescueMapEditMenu

        self.screens[self.SCREEN_RESCUE_EDIT] = RescueMapEditMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))

    def pushScreen(self, screenString, **kwargs):
        if len(self.screen_stack) == 0 and screenString == self.SCREEN_SIM:
            from ev3sim.simulation.loader import StateHandler

            StateHandler.instance.is_running = True
        self.screen_stack.append(screenString)
        if hasattr(self.screens[screenString], "ui_theme"):
            self.screens[screenString].ui_theme.load_theme(self.theme_path)
        self.screens[screenString].initWithKwargs(**kwargs)

    def popScreen(self):
        self.screens[self.screen_stack[-1]].onPop()
        self.screen_stack.pop()
        if len(self.screen_stack) == 0:
            from ev3sim.simulation.loader import StateHandler

            StateHandler.instance.is_running = False
        else:
            self.screens[self.screen_stack[-1]].regenerateObjects()

    def forceCloseError(self, errorInfo, errorButton=None):
        # We hit some error which is either unexpected or expected.
        # In either case remove all previous windows, give them the option to fix (highlight the user_config file for example)
        # And then close.
        self.screen_stack = []
        if errorButton is not None:
            self.pushScreen(
                self.SCREEN_UPDATE,
                panels=[
                    {
                        "text": errorInfo,
                        "type": "boolean",
                        "button_yes": errorButton[0],
                        "button_no": "Close",
                        "action": lambda v: v and errorButton[1](),
                    }
                ],
            )
        else:
            self.pushScreen(
                self.SCREEN_UPDATE,
                panels=[
                    {
                        "text": errorInfo,
                        "type": "accept",
                        "button": "Close",
                    }
                ],
            )

    def startScreen(self, push_screens=None, push_kwargss={}):
        from ev3sim import __version__ as version
        from ev3sim.file_helper import find_abs
        from ev3sim.simulation.loader import StateHandler

        pygame.init()
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        caption = f"ev3sim: MHS Robotics Club Simulator - version {version}"
        if ScreenObjectManager.NEW_VERSION:
            caption = f"[NEW VERSION AVAILABLE] {caption}"
        pygame.display.set_caption(caption)
        img_path = find_abs("Logo.png", allowed_areas=["package/assets/"])
        img = pygame.image.load(img_path)
        img.set_colorkey((255, 255, 255))
        pygame.display.set_icon(img)

        self.initScreens()
        for screen, kwargs in zip(push_screens, push_kwargss):
            self.pushScreen(screen, **kwargs)
        if not push_screens:
            self.pushScreen(self.SCREEN_MENU)

    def registerVisual(
        self, obj: "visual.objects.IVisualElement", key, kill_time=None, overwrite_key=False
    ) -> str:  # noqa: F821
        assert (
            key not in self.objects or overwrite_key
        ), f"Tried to register visual element to screen with key that is already in use: {key}"
        if key in self.objects:
            self.sorting_order.remove(key)
        self.objects[key] = obj
        # It is assumed the z-value of an item will note change as time progresses,
        # so no extra checks need to be made to sorting_order.
        # NOTE: We could speed this up with a binary search, possible performance gain with many objects.
        for x in range(len(self.sorting_order)):
            if self.objects[self.sorting_order[x]].zPos > obj.zPos:
                self.sorting_order.insert(x, key)
                break
        else:
            self.sorting_order.append(key)
        if kill_time is not None:
            for x in range(len(self.kill_keys)):
                if self.kill_keys[x][0] == key:
                    self.kill_keys[x] = [key, kill_time]
                    break
            else:
                self.kill_keys.append([key, kill_time])
        return key

    def unregisterVisual(self, key) -> "visual.objects.IVisualElement":  # noqa: F821
        obj = self.objects[key]
        del self.objects[key]
        # NOTE: We could speed this up with a binary search, possible performance gain with many objects.
        self.sorting_order.remove(key)
        return obj

    def registerObject(self, obj: "objects.base.BaseObject", key) -> str:  # noqa: F821
        if hasattr(obj, "visual") and obj.visual.visible:
            self.registerVisual(obj.visual, key)
        for i, child in enumerate(obj.children):
            self.registerObject(child, child.key)

    def applyToScreen(self, to_screen=None, bg=None):
        from ev3sim.simulation.loader import ScriptLoader

        blit_screen = self.screen if to_screen is None else to_screen

        blit_screen.fill(self.background_colour if bg is None else bg)

        to_remove = []
        for x in range(len(self.kill_keys)):
            self.kill_keys[x][1] -= 1 / ScriptLoader.instance.VISUAL_TICK_RATE
            if self.kill_keys[x][1] < 0:
                self.unregisterVisual(self.kill_keys[x][0])
                to_remove.append(x)
        for x in to_remove[::-1]:
            del self.kill_keys[x]

        if to_screen is None:
            # `.update` can call `applyToScreen`
            self.screens[self.screen_stack[-1]].update(1 / ScriptLoader.instance.VISUAL_TICK_RATE)
        if self.screen_stack[-1] == self.SCREEN_SIM or to_screen is not None:
            for key in self.sorting_order:
                if self.objects[key].sensorVisible:
                    self.objects[key].applyToScreen(blit_screen)
            self.sensorScreen = self.screen.copy()
            blit_screen.fill(self.background_colour if bg is None else bg)
            for key in self.sorting_order:
                self.objects[key].applyToScreen(blit_screen)
        if to_screen is None:
            # `.draw_ui` can call `applyToScreen`
            self.screens[self.screen_stack[-1]].draw_ui(blit_screen)
        if to_screen is None:
            pygame.display.update()

    def colourAtPixel(self, screen_position):
        return self.sensorScreen.get_at(screen_position)

    def handleEvents(self):
        from ev3sim.simulation.loader import StateHandler, ScriptLoader

        events = list(pygame.event.get()) + self.unhandled_events
        self.unhandled_events = []
        for event in events:
            if not StateHandler.instance.is_running:
                break
            self.screens[self.screen_stack[-1]].process_events(event)
            self.screens[self.screen_stack[-1]].handleEvent(event)
            if event.type == pygame.VIDEORESIZE:
                self.SCREEN_WIDTH, self.SCREEN_HEIGHT = event.size
                self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL = self.SCREEN_WIDTH, self.SCREEN_HEIGHT
                # Preserve a 4:3 ratio.
                if self.SCREEN_WIDTH / self.SCREEN_HEIGHT < 4 / 3:
                    self.SCREEN_HEIGHT = int(self.SCREEN_WIDTH * 3 / 4)
                else:
                    self.SCREEN_WIDTH = int(self.SCREEN_HEIGHT * 4 / 3)
                self.screen = pygame.display.set_mode(
                    (self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL), pygame.RESIZABLE
                )
                for key, menu in self.screens.items():
                    menu.setSize((self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL))
                for interactor in ScriptLoader.instance.active_scripts:
                    if hasattr(interactor, "setSize"):
                        interactor.setSize((self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL))
                for screen in self.screen_stack:
                    if screen == self.SCREEN_SIM:
                        for key in self.sorting_order:
                            self.objects[key].calculatePoints()
                    self.screens[screen].regenerateObjects()

            if event.type == pygame.QUIT:
                StateHandler.instance.is_running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if len(self.screen_stack) == 1:
                    StateHandler.instance.is_running = False
                else:
                    self.popScreen()
            if event.type == EV3SIM_BOT_COMMAND and event.command_type == CommandSystem.TYPE_DRAW:
                try:
                    possible_keys = []
                    for key in ScriptLoader.instance.object_map.keys():
                        if key.startswith(event.robot_id):
                            possible_keys.append(key)
                    if len(possible_keys) == 0:
                        break
                    possible_keys.sort(key=len)
                    parent_bot = ScriptLoader.instance.object_map[possible_keys[0]]

                    key = event.robot_id + "-" + event.payload["key"]
                    to_remove = []
                    for x, child in enumerate(parent_bot.children):
                        if child.key == key:
                            to_remove.append(x)
                    for x in to_remove[::-1]:
                        del parent_bot.children[x]

                    from ev3sim.objects.base import objectFactory

                    obj = objectFactory(
                        physics=False,
                        visual=event.payload["obj"],
                        position=event.payload["obj"].get("position", [0, 0]),
                        rotation=event.payload["obj"].get("rotation", 0),
                        key=key,
                    )
                    if event.payload.get("on_bot", False):
                        parent_bot.children.append(obj)
                        obj.parent = parent_bot
                        parent_bot.updateVisualProperties()
                    life = event.payload.get("life", 3)
                    self.registerVisual(obj.visual, key, kill_time=life, overwrite_key=True)
                except:
                    pass
        return events

    def relativeScreenScale(self):
        """Returns the relative scaling of the screen that has occur since the screen was first initialised."""
        # We maintain aspect ratio so no tuple is required.
        return self.SCREEN_WIDTH / self.original_SCREEN_WIDTH

    def captureBotImage(self, directory, filename):
        self.resetVisualElements()
        from os.path import join
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.robot import initialise_bot, RobotInteractor
        from ev3sim.simulation.randomisation import Randomiser

        Randomiser.createGlobalRandomiserWithSeed(0)
        ScriptLoader.instance.reset()
        ScriptLoader.instance.startUp()
        elems = {}
        initialise_bot(elems, find_abs(filename, [directory]), "", 0)
        ScriptLoader.instance.loadElements(elems.get("elements", []))
        for interactor in ScriptLoader.instance.active_scripts:
            if isinstance(interactor, RobotInteractor):
                interactor.connectDevices()
                interactor.initialiseDevices()
        for interactor in ScriptLoader.instance.active_scripts:
            interactor.startUp()
            interactor.tick(0)
            interactor.afterPhysics()
        screen = pygame.Surface((480, 480), pygame.SRCALPHA)
        custom_map = {
            "SCREEN_WIDTH": 480,
            "SCREEN_HEIGHT": 480,
            "MAP_WIDTH": 25,
            "MAP_HEIGHT": 25,
        }
        for elem in self.objects.values():
            elem.customMap = custom_map
            elem.calculatePoints()
        self.applyToScreen(screen, bg=pygame.Color(self.instance.background_colour))
        colorkey = pygame.Color(self.instance.background_colour)
        for x in range(480):
            for y in range(480):
                val = screen.get_at((x, y))
                val.a = 0 if (val.r == colorkey.r and val.g == colorkey.g and val.b == colorkey.b) else 255
                screen.set_at((x, y), val)
        self.resetVisualElements()
        ScriptLoader.instance.reset()
        config_path = join(find_abs(filename, [directory]), "config.bot")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        pygame.image.save(screen, join(find_abs(filename, [directory]), config.get("preview_path", "preview.png")))


screen_settings = {
    attr: ObjectSetting(ScreenObjectManager, attr)
    for attr in [
        "SCREEN_WIDTH",
        "SCREEN_HEIGHT",
        "MAP_WIDTH",
        "MAP_HEIGHT",
        "BACKGROUND_COLOUR",
    ]
}


def on_change_bg(new_val):
    ScreenObjectManager.instance.background_colour = new_val


def on_change_theme(new_val):
    ScreenObjectManager.theme_path = find_abs(new_val, allowed_areas=theme_locations())


screen_settings["BACKGROUND_COLOUR"].on_change = on_change_bg
screen_settings["theme"] = BindableValue("")
screen_settings["theme"].on_change = on_change_theme
