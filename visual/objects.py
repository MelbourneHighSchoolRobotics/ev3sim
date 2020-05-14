import numpy as np
import pygame
from typing import Optional, Tuple

from visual.manager import ScreenObjectManager
from visual.utils import hex_to_pycolor

class IVisualElement:

    # Position of a visual element is a x/y/z vector, with z representing the order in which objects are shown to the screen.
    # x/y ranges from 0-1, where 0,0 is the top-left corner of the screen, and x grows horizontally.
    # By convention, please let this position be the **centre** of your object.
    _position: np.ndarray
    # Rotation of a visual element is float, which should in theory range from 0 to 2pi, but should still work outside of those bounds.
    _rotation: float

    def __init__(self, **kwargs):
        self.init_from_kwargs(**kwargs)

    def init_from_kwargs(self, **kwargs):
        self.position = kwargs.get('position', np.array([0.5, 0.5, 0]))
        self.rotation = kwargs.get('rotation', 0)

    @property
    def position(self) -> np.ndarray:
        return self._position

    @property
    def rotation(self) -> float:
        return self._rotation

    @position.setter
    def position(self, value):
        if not isinstance(value, np.ndarray):
            self._position = np.array(value)
        else:
            self._position = value
        self.calculate_points()

    @rotation.setter
    def rotation(self, value):
        self._rotation = value
        self.calculate_points()

    def apply_to_screen(self):
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `apply_to_screen`")

    def calculate_points(self):
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `calculate_points`")

class Colorable(IVisualElement):
    _fill: Optional[Tuple[int]]
    _stroke: Optional[Tuple[int]]
    # These are relative to screen size (0-1).
    stroke_width: float

    def init_from_kwargs(self, **kwargs):
        super().init_from_kwargs(**kwargs)
        self.fill = kwargs.get('fill', '#ffffff')
        self.stroke = kwargs.get('stroke', None)
        self.stroke_width = kwargs.get('stroke_width', 0.02)

    @property
    def fill(self) -> Tuple[int]:
        return self._fill

    @fill.setter
    def fill(self, value):
        if isinstance(value, str):
            self._fill = hex_to_pycolor(value)
        else:
            self._fill = value

    @property
    def stroke(self) -> Tuple[int]:
        return self._stroke

    @stroke.setter
    def stroke(self, value):
        if isinstance(value, str):
            self._stroke = hex_to_pycolor(value)
        else:
            self._stroke = value

class Rectangle(Colorable):

    width: float
    height: float

    def init_from_kwargs(self, **kwargs):
        self.width = kwargs.get('width', 0.5)
        self.height = kwargs.get('height', 0.5)
        self.points = [None]*4
        super().init_from_kwargs(**kwargs)

    def calculate_points(self):
        try:
            tmp = self.width, self.height, self.rotation, self.position
        except:
            return
        mag = np.sqrt(pow(self.width, 2) + pow(self.height, 2))
        a1 = np.arctan(self.height / self.width)
        for i, a in enumerate([a1, np.pi-a1, np.pi+a1, -a1]):
            self.points[i] = (
                ScreenObjectManager.instance.screen_width * (self.position[0] + np.cos(self.rotation + a) * mag / 2),
                ScreenObjectManager.instance.screen_height * (self.position[1] + np.sin(self.rotation + a) * mag / 2),
            )

    def apply_to_screen(self):
        if self.fill:
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.fill, self.points)
        if self.stroke:
            # Stroke width is calculated based on screen width, I can't think of something cleaner than this.
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.stroke, self.points, int(self.stroke_width * ScreenObjectManager.instance.screen_width))

class Circle(Colorable):

    radius: float

    def init_from_kwargs(self, **kwargs):
        self.radius = kwargs.get('radius', 0.2)
        super().init_from_kwargs(**kwargs)

    def calculate_points(self):
        try:
            tmp = self.radius
        except:
            return
        self.point = (
            int(self.position[0] * ScreenObjectManager.instance.screen_width),
            int(self.position[1] * ScreenObjectManager.instance.screen_height),
        )
        self.v_radius = int(min(ScreenObjectManager.instance.screen_width, ScreenObjectManager.instance.screen_height) * self.radius)

    def apply_to_screen(self):
        if self.fill:
            pygame.draw.circle(ScreenObjectManager.instance.screen, self.fill, self.point, self.v_radius)
        if self.stroke:
            # Stroke width is calculated based on screen width, I can't think of something cleaner than this.
            pygame.draw.circle(ScreenObjectManager.instance.screen, self.stroke, self.point, self.v_radius, int(self.stroke_width * ScreenObjectManager.instance.screen_width))

def visualFactory(**options):
    if 'name' not in options:
        raise ValueError("Tried to generate visual element, but no 'name' field was supplied.")
    for klass in (Rectangle, Circle):
        if options['name'] == klass.__name__:
            r = klass()
            r.init_from_kwargs(**options)
            return r
    name = options['name']
    raise ValueError(f"Unknown visual element, {name}")
