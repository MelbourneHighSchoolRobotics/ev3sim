import pygame
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.world import World

class PauseInteractor(IInteractor):
    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            # Toggle pause state.
            World.instance.paused = not World.instance.paused