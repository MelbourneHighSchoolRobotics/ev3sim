import numpy as np
from typing import List

from visual.objects import IVisualElement, visualFactory

class BaseObject:

    parent: 'BaseObject'

    _position: np.ndarray
    _rotation: float

    visual: IVisualElement
    children: List['BaseObject']

    def init_from_kwargs(self, **kwargs):
        self._rotation = 0
        self.children = []
        self.parent = None
        if 'visual' in kwargs:
            self.visual = visualFactory(**kwargs['visual'])
        self.position = kwargs.get('position', (0.5, 0.5, 0))
        self.rotation = kwargs.get('rotation', 0)
        for child in kwargs.get('children', []):
            self.children.append(objectFactory(**child))
            self.children[-1].parent = self
        self.updateVisualProperties()

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if not isinstance(value, np.ndarray):
            self._position = np.array(value)
        else:
            self._position = value
        self.updateVisualProperties()

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        self._rotation = value
        self.updateVisualProperties()

    def updateVisualProperties(self):
        # This function assumes that the parent position and rotation are correct, and that a visual exists,
        # as otherwise each of these calls will have to go all the way up the parent tree.
        # In future this change could be made to support parts with no visual object.
        if self.visual is not None:
            if self.parent is None:
                self.visual.position = self.position
                self.visual.rotation = self.rotation
            elif self.parent.visual is not None:
                self.visual.position = self.parent.visual.position + np.array([
                    self.position[0] * np.cos(self.parent.visual.rotation) - self.position[1] * np.sin(self.parent.visual.rotation),
                    self.position[1] * np.cos(self.parent.visual.rotation) + self.position[0] * np.sin(self.parent.visual.rotation),
                    self.position[2]
                ])
                self.visual.rotation = self.parent.visual.rotation + self.rotation
            for child in self.children:
                child.updateVisualProperties()

def objectFactory(**options):
    r = BaseObject()
    r.init_from_kwargs(**options)
    return r
