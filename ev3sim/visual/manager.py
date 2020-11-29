from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.settings import BindableValue, ObjectSetting
import pygame
import pygame.freetype
from typing import Dict, List, Tuple

import ev3sim.visual.utils as utils


class ScreenObjectManager:

    instance: "ScreenObjectManager"

    SCREEN_MENU = "MAIN_MENU"
    SCREEN_SIM = "SIMULATOR"
    SCREEN_BATCH = "BATCH_SELECT"
    SCREEN_BOTS = "BOT_SELECT"
    SCREEN_SETTINGS = "SETTINGS"
    SCREEN_WORKSPACE = "WORKSPACE"

    screen_stack = []

    screen: pygame.Surface
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 960
    MAP_WIDTH: float = 200
    MAP_HEIGHT: float = 200
    BACKGROUND_COLOUR = "#000000"

    _background_colour: Tuple[int]

    objects: Dict[str, "visual.objects.IVisualElement"]  # noqa: F821
    sorting_order: List[str]

    # This needs to be provided in settings.
    theme_path = ""

    def __init__(self, **kwargs):
        ScreenObjectManager.instance = self
        self.objects = {}
        self.sorting_order = []
        self.screen_stack = []
        self.initFromKwargs(**kwargs)

    def resetVisualElements(self):
        self.sorting_order = []
        self.objects = {}

    def initFromKwargs(self, **kwargs):
        self.original_SCREEN_WIDTH = self.SCREEN_WIDTH
        self.original_SCREEN_HEIGHT = self.SCREEN_HEIGHT
        self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL = self.SCREEN_WIDTH, self.SCREEN_HEIGHT
        self.background_colour = self.BACKGROUND_COLOUR

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
        # Workspace select dialog
        from ev3sim.visual.menus.workspace_menu import WorkspaceMenu

        self.screens[self.SCREEN_WORKSPACE] = WorkspaceMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Menu screen
        from ev3sim.visual.menus.main import MainMenu

        self.screens[self.SCREEN_MENU] = MainMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Batch screen
        from ev3sim.visual.menus.batch_select import BatchMenu

        self.screens[self.SCREEN_BATCH] = BatchMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Bots screen
        from ev3sim.visual.menus.bot_menu import BotMenu

        self.screens[self.SCREEN_BOTS] = BotMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))

        # Simulator screen
        from ev3sim.visual.menus.sim_menu import SimulatorMenu

        self.screens[self.SCREEN_SIM] = SimulatorMenu()
        # Settings generic screen
        from ev3sim.visual.settings.menu import SettingsMenu

        self.screens[self.SCREEN_SETTINGS] = SettingsMenu((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))

    # TODO: Animate screen popping? Add this as an option?

    def pushScreen(self, screenString, **kwargs):
        self.screen_stack.append(screenString)
        if hasattr(self.screens[screenString], "ui_theme"):
            self.screens[screenString].ui_theme.load_theme(self.theme_path)
        self.screens[screenString].initWithKwargs(**kwargs)

    def popScreen(self):
        self.screens[self.screen_stack[-1]].onPop()
        self.screen_stack.pop()

    def startScreen(self):
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
        if not StateHandler.WORKSPACE_FOLDER:
            self.pushScreen(self.SCREEN_WORKSPACE)
        else:
            self.pushScreen(self.SCREEN_MENU)

    def registerVisual(self, obj: "visual.objects.IVisualElement", key) -> str:  # noqa: F821
        assert (
            key not in self.objects
        ), f"Tried to register visual element to screen with key that is already in use: {key}"
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
        return key

    def unregisterVisual(self, key) -> "visual.objects.IVisualElement":  # noqa: F821
        obj = self.objects[key]
        del self.objects[key]
        # NOTE: We could speed this up with a binary search, possible performance gain with many objects.
        self.sorting_order.remove(key)
        return obj

    def registerObject(self, obj: "objects.base.BaseObject", key) -> str:  # noqa: F821
        if obj.visual is not None and obj.visual.visible:
            self.registerVisual(obj.visual, key)
        for i, child in enumerate(obj.children):
            self.registerObject(child, child.key)

    def applyToScreen(self, to_screen=None, bg=None):
        from ev3sim.simulation.loader import ScriptLoader

        blit_screen = self.screen if to_screen is None else to_screen

        blit_screen.fill(self.background_colour if bg is None else bg)
        self.screens[self.screen_stack[-1]].update(1 / ScriptLoader.instance.VISUAL_TICK_RATE)
        if self.screen_stack[-1] == self.SCREEN_SIM or to_screen is not None:
            for key in self.sorting_order:
                if self.objects[key].sensorVisible:
                    self.objects[key].applyToScreen(blit_screen)
            self.sensorScreen = self.screen.copy()
            blit_screen.fill(self.background_colour if bg is None else bg)
            for key in self.sorting_order:
                self.objects[key].applyToScreen(blit_screen)
        else:
            self.screens[self.screen_stack[-1]].draw_ui(blit_screen)
        pygame.display.update()

    def colourAtPixel(self, screen_position):
        return self.sensorScreen.get_at(screen_position)

    def handleEvents(self):
        from ev3sim.simulation.loader import StateHandler

        events = pygame.event.get()
        for event in events:
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
                    if key != self.SCREEN_SIM:
                        menu.setSize((self._SCREEN_WIDTH_ACTUAL, self._SCREEN_HEIGHT_ACTUAL))
                for screen in self.screen_stack:
                    if screen == self.SCREEN_SIM:
                        for key in self.sorting_order:
                            self.objects[key].calculatePoints()
                    else:
                        self.screens[screen].sizeObjects()

            if event.type == pygame.QUIT:
                StateHandler.instance.is_running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if len(self.screen_stack) == 1:
                    StateHandler.instance.is_running = False
                else:
                    self.popScreen()
        return events

    def relativeScreenScale(self):
        """Returns the relative scaling of the screen that has occur since the screen was first initialised."""
        # We maintain aspect ratio so no tuple is required.
        return self.SCREEN_WIDTH / self.original_SCREEN_WIDTH

    def captureBotImage(self, directory, filename, bg=None):
        self.resetVisualElements()
        from os.path import join
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.robot import initialise_bot, RobotInteractor
        from ev3sim.simulation.randomisation import Randomiser

        Randomiser.createGlobalRandomiserWithSeed(0)
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
        screen = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        SCALE_AMOUNT = 5
        for elem in self.objects.values():
            elem.scaleAtPosition(SCALE_AMOUNT)
        self.applyToScreen(screen, bg=bg)
        top_left = utils.worldspace_to_screenspace((-11 * SCALE_AMOUNT, 11 * SCALE_AMOUNT))
        bot_right = utils.worldspace_to_screenspace((11 * SCALE_AMOUNT, -11 * SCALE_AMOUNT))
        cropped = pygame.Surface((bot_right[0] - top_left[0], bot_right[1] - top_left[1]))
        cropped.blit(screen, (0, 0), (top_left[0], top_left[1], bot_right[0] - top_left[0], bot_right[1] - top_left[1]))
        self.resetVisualElements()
        ScriptLoader.instance.reset()
        if directory.startswith("workspace"):
            dirname = find_abs_directory("workspace/images/", create=True)
        elif directory.startswith("package"):
            dirname = find_abs_directory("packages/assets/bots")
        else:
            raise ValueError(f"Don't know where to save the preview for {filename} in {directory}")
        pygame.image.save(cropped, join(dirname, filename.replace(".yaml", ".png")))


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
    ScreenObjectManager.theme_path = find_abs(new_val, allowed_areas=["local", "package/assets"])


screen_settings["BACKGROUND_COLOUR"].on_change = on_change_bg
screen_settings["theme"] = BindableValue("")
screen_settings["theme"].on_change = on_change_theme
