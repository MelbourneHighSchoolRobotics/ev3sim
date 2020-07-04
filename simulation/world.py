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
        # TODO: Add some options here, and do physics.
        # I just check for collisions and scream if this is the case.
        for i, obj in enumerate(self.objects):
            for obj2 in self.objects[i+1:]:
                res = obj.collider.getCollisionInfo(obj2.collider)
                if res['collision']:
                    from visual.objects import visualFactory
                    p = res['world_space_position']
                    if len(p) == 3:
                        p[2] = 10
                    else:
                        p = np.append(p, [10])
                    obj = visualFactory(**{
                        'name': 'Circle',
                        'radius': 3,
                        'fill': '#ffffff',
                        'stroke_width': 0,
                        'position': p
                    })
                    if 'point' in ScreenObjectManager.instance.objects:
                        ScreenObjectManager.instance.unregisterVisual('point')
                    ScreenObjectManager.instance.registerVisual(obj, 'point')
                    
