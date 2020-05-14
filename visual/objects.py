import numpy as np
import pygame
from typing import Optional

from visual.manager import ScreenObjectManager
from visual.utils import hex_to_pycolor

class IVisualElement:

    # Position of a visual element is a x/y/z vector, with z representing the order in which objects are shown to the screen.
    # x/y ranges from 0-1, where 0,0 is the top-left corner of the screen, and x grows horizontally.
    # By convention, please let this position be the **centre** of your object.
    position: np.ndarray
    # Rotation of a visual element is float, which should in theory range from 0 to 2pi, but should still work outside of those bounds.
    rotation: float

    def __init__(self, **kwargs):
        self.init_from_kwargs(**kwargs)

    def init_from_kwargs(self, **kwargs):
        self.position = kwargs.get('position', np.array([0.5, 0.5, 0]))
        self.rotation = kwargs.get('rotation', 0)

    def apply_to_screen(self):
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `apply_to_screen`")

class Rectangle(IVisualElement):

    fill: Optional[str]
    stroke: Optional[str]
    # These are relative to screen size (0-1).
    stroke_width: float
    width: float
    height: float

    def init_from_kwargs(self, **kwargs):
        super().init_from_kwargs(**kwargs)
        self.fill = kwargs.get('fill', hex_to_pycolor('#ffffff'))
        self.stroke = kwargs.get('stroke', None)
        self.width = kwargs.get('width', 0.5)
        self.height = kwargs.get('height', 0.5)
        self.stroke_width = kwargs.get('stroke_width', self.width / 20)
        self.points = [None]*4

    def calculate_polygon_points(self):
        mag = np.sqrt(pow(self.width, 2) + pow(self.height, 2))
        a1 = np.arctan(self.height / self.width)
        for i, a in enumerate([a1, np.pi-a1, np.pi+a1, -a1]):
            self.points[i] = (
                ScreenObjectManager.instance.screen_width * (self.position[0] + np.cos(self.rotation + a) * mag / 2),
                ScreenObjectManager.instance.screen_height * (self.position[1] + np.sin(self.rotation + a) * mag / 2),
            )

    def apply_to_screen(self):
        self.calculate_polygon_points()
        if self.fill:
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.fill, self.points)
        if self.stroke:
            # Stroke width is calculated based on screen width, I can't think of something cleaner than this.
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.stroke, self.points, int(self.stroke_width * ScreenObjectManager.instance.screen_width))
