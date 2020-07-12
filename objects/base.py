import numpy as np
from typing import List

from visual.objects import IVisualElement, visualFactory
from objects.colliders import Collider, colliderFactory

class BaseObject:

    parent: 'BaseObject'

    _position: np.ndarray
    _rotation: float

    visual: IVisualElement
    children: List['BaseObject']

    def initFromKwargs(self, **kwargs):
        self._rotation = 0
        self.children = []
        self.parent = None
        if 'visual' in kwargs:
            self.visual = visualFactory(**kwargs['visual'])
        self.position = kwargs.get('position', (0.5, 0.5))
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
        if self.visual is not None:
            if self.parent is None:
                self.visual.position = self.position
                self.visual.rotation = self.rotation
            elif self.parent.visual is not None:
                self.visual.position = self.parent.visual.position + np.array([
                    self.position[0] * np.cos(self.parent.visual.rotation) - self.position[1] * np.sin(self.parent.visual.rotation),
                    self.position[1] * np.cos(self.parent.visual.rotation) + self.position[0] * np.sin(self.parent.visual.rotation)
                ])
                self.visual.rotation = self.parent.visual.rotation + self.rotation
            for child in self.children:
                child.updateVisualProperties()

class PhysicsObject(BaseObject):

    # TODO: Use these
    velocity: np.ndarray
    angular_velocity: float

    _force: np.ndarray
    _torque: float

    mass: float
    inertia: float

    friction_coefficient: float
    restitution_coefficient: float

    collider: Collider

    static: bool

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        if 'collider' not in kwargs:
            raise ValueError("Collider not defined.")
        if kwargs['collider'] == 'inherit':
            self.collider = self.visual.generateCollider(self)
        else:
            self.collider = colliderFactory(self, **kwargs['collider'])
        self.mass = kwargs.get('mass', 1)
        self.static = kwargs.get('static', False)
        self.friction_coefficient = kwargs.get('friction', 0.1)
        self.restitution_coefficient = kwargs.get('restitution', 0.7)
        self.collider.generateExtraPhysicsAttributes()
        self._force = np.array([.0, .0])
        self.velocity = np.array([.0, .0])
        self._torque = 0
        self.angular_velocity = 0

    def updatePhysics(self, dt):
        # Create a friction force based on previous velocity
        self.apply_force(-self.mass * self.velocity * self.friction_coefficient)

        # Acceleration is set to 0 each update - no leakage.
        acceleration = self._force / self.mass
        self.velocity += acceleration * dt
        self.position += self.velocity * dt

        # Same with angular acceleration
        angular_acceleration = self._torque / self.inertia
        self.angular_velocity += angular_acceleration * dt
        self.rotation += self.angular_velocity * dt

        # Clear forces for next update.
        self._force = np.array([0., 0.])

    def apply_force(self, f, pos=None):
        """Apply a force to the object, from a relative position"""
        self._force += f
        if pos is not None:
            self.apply_torque(np.cross(pos, f))
    
    def apply_torque(self, t):
        self._torque += t

def objectFactory(**options):
    if options.get('physics', False):
        r = PhysicsObject()
    else:
        r = BaseObject()
    r.initFromKwargs(**options)
    return r
