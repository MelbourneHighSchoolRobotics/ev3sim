import numpy as np
import pygame
from simulation.interactor import IInteractor
from simulation.world import World
from objects.base import objectFactory
from visual.utils import screenspace_to_worldspace

class PickUpInteractor(IInteractor):

    # Variables for grabbing an object
    obj_grabbed = False
    obj_rel_pos = None
    obj_m_pos = None
    obj = None

    # Variables for calculating velocity of mouse.
    TOTAL_POSITIONS = 5
    position_index = 0
    position_length = 0
    VELOCITY_MULT = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.positions = [None]*10

    def tick(self, tick):
        super().tick(tick)
        if not self.obj_grabbed:
            self.position_length = 0
        if self.obj_grabbed:
            self.obj.position = self.obj_rel_pos + self.obj_m_pos
            idx = (self.position_index + self.position_length) % self.TOTAL_POSITIONS
            self.positions[(self.position_index + self.position_length) % self.TOTAL_POSITIONS] = self.obj_m_pos
            self.position_length = min(self.position_length+1, 10)
            self.position_index = (idx - self.position_length + 1 + self.TOTAL_POSITIONS) % self.TOTAL_POSITIONS
            # Ensure tick specific forces are still reset. Thanks Angus :D
            self.obj._force = np.array([0.0, 0.0])
            self.obj._torque = 0

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
            # Give velocity based on previous mouse positions.
            if self.position_length != 0:
                differences = sum(
                    (x+1) / self.position_length * (self.positions[(self.position_index + x+1) % self.TOTAL_POSITIONS] - self.positions[(self.position_index + x) % self.TOTAL_POSITIONS])
                    for x in range(self.position_length-1)
                )
                self.obj.velocity = self.VELOCITY_MULT * differences
        if event.type == pygame.MOUSEMOTION and self.obj_grabbed:
            self.obj_m_pos = screenspace_to_worldspace(event.pos)