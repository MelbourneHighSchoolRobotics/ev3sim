import numpy as np
import pygame
import pymunk
import pyperclip
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.world import World
from ev3sim.objects.base import objectFactory
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.objects.base import STATIC_CATEGORY


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
        self.positions = [None] * 10

    def tick(self, tick):
        super().tick(tick)
        if not self.obj_grabbed:
            self.position_length = 0
        if self.obj_grabbed:
            if not getattr(self.obj, "clickable", True):
                self.obj_grabbed = False
            else:
                self.obj.body.position = self.obj_rel_pos + self.obj_m_pos
                idx = (self.position_index + self.position_length) % self.TOTAL_POSITIONS
                self.positions[(self.position_index + self.position_length) % self.TOTAL_POSITIONS] = self.obj_m_pos
                self.position_length = min(self.position_length + 1, 10)
                self.position_index = (idx - self.position_length + 1 + self.TOTAL_POSITIONS) % self.TOTAL_POSITIONS

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                m_pos, 0.0, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ STATIC_CATEGORY)
            )
            if shapes:
                max_z = max(pq.shape.obj.clickZ for pq in shapes)
                shapes = [pq for pq in shapes if pq.shape.obj.clickZ == max_z]
                self.obj = shapes[0].shape.obj
                if getattr(self.obj, "clickable", True):
                    self.obj.body.velocity = np.array([0.0, 0.0])
                    self.obj_grabbed = True
                    self.obj_rel_pos = self.obj.position - m_pos
                    self.obj_m_pos = m_pos
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # If a robot is right clicked, copy it's ID for use in the attach script.
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                m_pos, 0.0, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ STATIC_CATEGORY)
            )
            if shapes:
                max_z = max(pq.shape.obj.clickZ for pq in shapes)
                shapes = [pq for pq in shapes if pq.shape.obj.clickZ == max_z]
                self.obj = shapes[0].shape.obj
                if hasattr(self.obj, "robot_class"):
                    pyperclip.copy(self.obj.robot_class.ID)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.obj_grabbed:
            self.obj_grabbed = False
            # Give velocity based on previous mouse positions.
            if self.position_length != 0:
                differences = sum(
                    (x + 1)
                    / self.position_length
                    * (
                        self.positions[(self.position_index + x + 1) % self.TOTAL_POSITIONS]
                        - self.positions[(self.position_index + x) % self.TOTAL_POSITIONS]
                    )
                    for x in range(self.position_length - 1)
                )
                # Sum will return 0 if position length is 0 - we need to handle this.
                if isinstance(differences, int):
                    differences = np.array([0, 0])
                self.obj.body.velocity = self.VELOCITY_MULT * differences
        if event.type == pygame.MOUSEMOTION and self.obj_grabbed:
            self.obj_m_pos = screenspace_to_worldspace(event.pos)
