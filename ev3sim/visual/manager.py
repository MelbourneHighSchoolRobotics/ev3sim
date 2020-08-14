import pygame
import pygame.freetype
from typing import Dict, List, Tuple

import ev3sim.visual.utils as utils

class ScreenObjectManager:

    instance: 'ScreenObjectManager'

    screen: pygame.Surface
    screen_width: int
    screen_height: float

    _background_color: Tuple[int]

    objects: Dict[str, 'visual.objects.IVisualElement'] # noqa: F821
    sorting_order: List[str]

    def __init__(self, **kwargs):
        ScreenObjectManager.instance = self
        self.objects = {}
        self.sorting_order = []
        self.initFromKwargs(**kwargs)

    def initFromKwargs(self, **kwargs):
        self.screen_width = kwargs.get('screen_width', 640)
        self.screen_height = kwargs.get('screen_height', 480)
        # NOTE: TEMPORARY - this would describe the dimensions of the simulated map vs the screen dimensions.
        self.map_width = kwargs.get('map_width', 210)
        self.map_height = kwargs.get('map_height', 160)
        self.background_color = kwargs.get('background_color', '#000000')

    @property
    def background_color(self):
        return self._background_color

    @background_color.setter
    def background_color(self, value):
        if isinstance(value, str):
            if value in utils.GLOBAL_COLOURS:
                value = utils.GLOBAL_COLOURS[value]
            if value.startswith('#'):
                value = value[1:]
            self._background_color = utils.hex_to_pycolor(value)
        else:
            self._background_color = value

    def startScreen(self):
        from ev3sim.file_helper import find_abs
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption('MHS Robotics Club Simulator')
        img_path = find_abs('Logo.png', allowed_areas=['package/assets/'])
        img = pygame.image.load(img_path)
        img.set_colorkey((255, 255, 255))
        pygame.display.set_icon(img)

    def registerVisual(self, obj: 'visual.objects.IVisualElement', key) -> str: # noqa: F821
        assert key not in self.objects, f"Tried to register visual element to screen with key that is already in use: {key}"
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

    def unregisterVisual(self, key) -> 'visual.objects.IVisualElement': # noqa: F821
        obj = self.objects[key]
        del self.objects[key]
        # NOTE: We could speed this up with a binary search, possible performance gain with many objects.
        self.sorting_order.remove(key)
        return obj

    def registerObject(self, obj: 'objects.base.BaseObject', key) -> str: # noqa: F821
        if obj.visual is not None and obj.visual.visible:
            self.registerVisual(obj.visual, key)
        for i, child in enumerate(obj.children):
            new_key = key + str(child.__class__.__name__) + str(i)
            self.registerObject(child, new_key)

    def applyToScreen(self):
        self.screen.fill(self.background_color)
        for key in self.sorting_order:
            if self.objects[key].sensorVisible:
                self.objects[key].applyToScreen()
        self.sensorScreen = self.screen.copy()
        for key in self.sorting_order:
            if not self.objects[key].sensorVisible:
                self.objects[key].applyToScreen()
        pygame.display.update()

    def colourAtPixel(self, screen_position):
        return self.sensorScreen.get_at(screen_position)

    def handleEvents(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                from ev3sim.simulation.loader import ScriptLoader
                pygame.quit()
                ScriptLoader.instance.running = False
            yield event
