import numpy as np
import pymunk
from typing import List

from ev3sim.visual.objects import IVisualElement, visualFactory
from ev3sim.simulation.world import stop_on_pause

DYNAMIC_CATEGORY = 0b10
STATIC_CATEGORY = 0b100


class BaseObject:

    parent: "BaseObject"

    _position: np.ndarray
    _rotation: float

    visual: IVisualElement
    children: List["BaseObject"]

    def initFromKwargs(self, **kwargs):
        self._rotation = 0
        self.children = []
        self.parent = None
        if "visual" in kwargs:
            self.visual = visualFactory(**kwargs["visual"])
        self.position = kwargs.get("position", (0.5, 0.5))
        self.rotation = kwargs.get("rotation", 0)
        for i, child in enumerate(kwargs.get("children", [])):
            child["key"] = kwargs["key"] + f"-child-{i}"
            self.children.append(objectFactory(**child))
            self.children[-1].parent = self
        self.key = kwargs["key"]
        self.updateVisualProperties()

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if not isinstance(value, np.ndarray):
            self._position = np.array([float(f) for f in value])
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
        if hasattr(self, "visual"):
            if self.parent is None:
                self.visual.position = self.position
                self.visual.rotation = self.rotation
            elif self.parent.visual is not None:
                self.visual.position = self.parent.visual.position + np.array(
                    [
                        self.position[0] * np.cos(self.parent.visual.rotation)
                        - self.position[1] * np.sin(self.parent.visual.rotation),
                        self.position[1] * np.cos(self.parent.visual.rotation)
                        + self.position[0] * np.sin(self.parent.visual.rotation),
                    ]
                )
                self.visual.rotation = self.parent.visual.rotation + self.rotation
            for child in self.children:
                child.updateVisualProperties()


class PhysicsObject(BaseObject):

    mass: float

    friction_coefficient: float
    restitution_coefficient: float

    sensor: bool
    # clickZ tells the object what level of the hierarchy it is at, onClick handlers will only target objects selected with the highest clickZ.
    clickZ: float

    shape: pymunk.Shape

    static: bool

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        self.mass = kwargs.get("mass", 1)
        self.static = kwargs.get("static", False)
        self.clickZ = kwargs.get("clickZ", 0)
        self.friction_coefficient = kwargs.get("friction", 1)
        self.restitution_coefficient = kwargs.get("restitution", 0.7)
        self.sensor = kwargs.get("sensor", False)
        self.body, self.shape = self.visual.generateBodyAndShape(self)
        self.shapes = [self.shape]
        self.shape.obj = self
        self.body.position = self.position + self.visual.getPositionAnchorOffset()
        for child in self.children:
            if isinstance(child, PhysicsObject):
                child.body, child.shape = child.visual.generateBodyAndShape(
                    child, body=self.body, rel_pos=child.position
                )
                child.shape.obj = self
                self.shapes.append(child.shape)

    def update(self):
        if not self.static:
            self.position = self.body.position - self.visual.getPositionAnchorOffset()
            self.rotation = self.body.angle
            self.update_velocities()

    @stop_on_pause
    def update_velocities(self):
        # No angular friction or air resistance/velocity dampening, so do this.
        self.body.angular_velocity *= self.friction_coefficient
        self.body.velocity *= self.friction_coefficient

    @stop_on_pause
    def apply_force(self, f, pos=None):
        """Apply a force to the object, from a relative position"""
        if pos is None:
            pos = np.array([0.0, 0.0])
        self.shape.body.apply_force_at_local_point(f, pos)


def objectFactory(**options):
    if options.get("physics", False):
        r = PhysicsObject()
    else:
        r = BaseObject()
    r.initFromKwargs(**options)
    return r
