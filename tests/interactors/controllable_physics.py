import pygame
import numpy as np
from tests.interactors.spawner import SpawnerInteractor

class ControllablePhysics(SpawnerInteractor):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accel = kwargs.get('accel', 1)
        self.f = np.array([0, 0])

    def tick(self, tick):
        self.object_map['phys_obj'].apply_force(self.f)
        return False

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                self.f += np.array([-self.accel, 0])
            if event.key == pygame.K_d:
                self.f += np.array([self.accel, 0])
            if event.key == pygame.K_w:
                self.f += np.array([0, self.accel])
            if event.key == pygame.K_s:
                self.f += np.array([0, -self.accel])
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                self.f -= np.array([-self.accel, 0])
            if event.key == pygame.K_d:
                self.f -= np.array([self.accel, 0])
            if event.key == pygame.K_w:
                self.f -= np.array([0, self.accel])
            if event.key == pygame.K_s:
                self.f -= np.array([0, -self.accel])