import numpy as np
import pygame
from typing import Optional, Tuple

from visual.manager import ScreenObjectManager
from visual.utils import hex_to_pycolor, worldspace_to_screenspace
from objects.utils import local_space_to_world_space

class IVisualElement:

    # Position of a visual element is a x/y/z vector, with z representing the order in which objects are shown to the screen.
    # x/y has 0,0 at the centre of the screen, and x grows horizontally to the right, while y grows vertically upwards.
    # By convention, please let this position be the **centre** of your object.
    _position: np.ndarray
    # Rotation of a visual element is float, which should in theory range from 0 to 2pi, but should still work outside of those bounds.
    _rotation: float

    def __init__(self, **kwargs):
        self.initFromKwargs(**kwargs)

    def initFromKwargs(self, **kwargs):
        self.position = kwargs.get('position', [0, 0, 0])
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
        self.calculatePoints()

    @rotation.setter
    def rotation(self, value):
        self._rotation = value
        self.calculatePoints()

    def applyToScreen(self):
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `applyToScreen`")

    def calculatePoints(self):
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `calculatePoints`")

class Colorable(IVisualElement):
    _fill: Optional[Tuple[int]]
    _stroke: Optional[Tuple[int]]
    stroke_width: float

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        self.fill = kwargs.get('fill', '#ffffff')
        self.stroke = kwargs.get('stroke', None)
        self.stroke_width = kwargs.get('stroke_width', 1)

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

class Polygon(Colorable):

    verts: np.array

    def initFromKwargs(self, **kwargs):
        self.verts = kwargs.get('verts')
        self.points = [None]*len(self.verts)
        super().initFromKwargs(**kwargs)

    def calculatePoints(self):
        try:
            tmp = self.rotation, self.position
        except:
            return
        for i, v in enumerate(self.verts):
            self.points[i] = worldspace_to_screenspace(local_space_to_world_space(v, self.rotation, self.position))

    def applyToScreen(self):
        if self.fill:
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.fill, self.points)
        if self.stroke:
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.stroke, self.points, int(self.stroke_width * ScreenObjectManager.instance.screen_width / ScreenObjectManager.instance.map_width))

class Rectangle(Polygon):

    width: float
    height: float

    def initFromKwargs(self, **kwargs):
        self.width = kwargs.get('width', 20)
        self.height = kwargs.get('height', 20)
        kwargs['verts'] = [
            [self.width, self.height],
            [-self.width, self.height],
            [-self.width, -self.height],
            [self.width, -self.height],
        ]
        super().initFromKwargs(**kwargs)

class Circle(Colorable):

    radius: float

    def initFromKwargs(self, **kwargs):
        self.radius = kwargs.get('radius', 20)
        super().initFromKwargs(**kwargs)

    def calculatePoints(self):
        try:
            tmp = self.radius
        except:
            return
        self.point = worldspace_to_screenspace(self.position)
        self.v_radius = int(ScreenObjectManager.instance.screen_height / ScreenObjectManager.instance.map_height * self.radius)

    def applyToScreen(self):
        if self.fill:
            pygame.draw.circle(ScreenObjectManager.instance.screen, self.fill, self.point, self.v_radius)
        if self.stroke:
            pygame.draw.circle(ScreenObjectManager.instance.screen, self.stroke, self.point, self.v_radius, int(self.stroke_width * ScreenObjectManager.instance.screen_width / ScreenObjectManager.instance.map_width))

def visualFactory(**options):
    if 'name' not in options:
        raise ValueError("Tried to generate visual element, but no 'name' field was supplied.")
    for klass in (Polygon, Rectangle, Circle):
        if options['name'] == klass.__name__:
            r = klass(**options)
            return r
    name = options['name']
    raise ValueError(f"Unknown visual element, {name}")
