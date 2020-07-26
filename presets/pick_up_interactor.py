import numpy as np
import pygame
from simulation.interactor import IInteractor
from simulation.world import World
from objects.base import objectFactory
from visual.utils import screenspace_to_worldspace

class PickUpInteractor(IInteractor):

    # Constants for grabbing an object
    obj_grabbed = False
    obj_rel_pos = None
    obj_m_pos = None
    obj = None

    def tick(self, tick):
        super().tick(tick)
        if self.obj_grabbed:
            self.obj.position = self.obj_rel_pos + self.obj_m_pos

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            collider = objectFactory(**{
                'physics': True,
                'position': m_pos,
                'collider': {
                    'name': 'Point'
                }
            }).collider
            for obj in World.instance.objects:
                if obj.collider.getCollisionInfo(collider)["collision"]:
                    # Grab the object!
                    obj.velocity = np.array([0.0, 0.0])
                    World.instance.unregisterObject(obj)
                    self.obj = obj
                    self.obj_grabbed = True
                    self.obj_rel_pos = obj.position - m_pos
                    self.obj_m_pos = m_pos
                    break
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.obj_grabbed:
            self.obj_grabbed = False
            World.instance.registerObject(self.obj)
        if event.type == pygame.MOUSEMOTION and self.obj_grabbed:
            self.obj_m_pos = screenspace_to_worldspace(event.pos)