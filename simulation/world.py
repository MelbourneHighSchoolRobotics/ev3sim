import pygame
import numpy as np
from objects.base import PhysicsObject
from visual.manager import ScreenObjectManager
from visual.utils import worldspace_to_screenspace

class World:

    instance: 'World' = None

    def __init__(self):
        World.instance = self
        self.objects = []
    
    def registerObject(self, obj: PhysicsObject):
        self.objects.append(obj)
    
    def tick(self, dt):
        for obj in self.objects:
            obj.updatePhysics(dt)
        # In batches, try to handle collisions between all objects, handling immovable objects first.
        for i, obj in enumerate(self.objects):
            for obj2 in self.objects[i+1:]:
                res = obj.collider.getCollisionInfo(obj2.collider)
                if res['collision']:
                    # For now, just move objects apart.
                    obj.position += res['collision_vector'] / 2
                    obj2.position -= res['collision_vector'] / 2
                    
