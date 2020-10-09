import pygame
import pygame.freetype
from typing import Dict, List, Tuple

import ev3sim.visual.utils as utils


class ScreenObjectManager:

    instance: "ScreenObjectManager"

    screen: pygame.Surface
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 960
    MAP_WIDTH: float = 200
    MAP_HEIGHT: float = 200
    BACKGROUND_COLOUR = "#000000"

    _background_colour: Tuple[int]

    objects: Dict[str, "visual.objects.IVisualElement"]  # noqa: F821
    sorting_order: List[str]

    def __init__(self, **kwargs):
        ScreenObjectManager.instance = self
        self.objects = {}
        self.sorting_order = []
        self.initFromKwargs(**kwargs)

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

    def startScreen(self):
        from ev3sim import __version__ as version
        from ev3sim.file_helper import find_abs

        pygame.init()
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        caption = f"ev3sim: MHS Robotics Club Simulator - version {version}"
        if hasattr(ScreenObjectManager, "BATCH_FILE"):
            caption = caption + f" - {ScreenObjectManager.BATCH_FILE}/{ScreenObjectManager.PRESET_FILE}"
        else:
            caption = caption + f" - {ScreenObjectManager.PRESET_FILE}"
        if ScreenObjectManager.NEW_VERSION:
            caption = f"[NEW VERSION AVAILABLE] {caption}"
        pygame.display.set_caption(caption)
        img_path = find_abs("Logo.png", allowed_areas=["package/assets/"])
        img = pygame.image.load(img_path)
        img.set_colorkey((255, 255, 255))
        pygame.display.set_icon(img)

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

    def applyToScreen(self):
        self.screen.fill(self.background_colour)
        for key in self.sorting_order:
            if self.objects[key].sensorVisible:
                self.objects[key].applyToScreen()
        self.sensorScreen = self.screen.copy()
        self.screen.fill(self.background_colour)
        for key in self.sorting_order:
            self.objects[key].applyToScreen()
        pygame.display.update()

    def colourAtPixel(self, screen_position):
        return self.sensorScreen.get_at(screen_position)

    def handleEvents(self):
        for event in pygame.event.get():
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
                for key in self.sorting_order:
                    self.objects[key].calculatePoints()
            if event.type == pygame.QUIT:
                from ev3sim.simulation.loader import ScriptLoader

                pygame.quit()
                ScriptLoader.instance.running = False
            yield event

    def relativeScreenScale(self):
        """Returns the relative scaling of the screen that has occur since the screen was first initialised."""
        # We maintain aspect ratio so no tuple is required.
        return self.SCREEN_WIDTH / self.original_SCREEN_WIDTH
