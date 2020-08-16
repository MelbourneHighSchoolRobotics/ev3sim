import pygame
import pymunk
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World

class PauseInteractor(IInteractor):
    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            # Toggle pause state.
            World.instance.paused = not World.instance.paused
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            # Click event for object['controls'] should go here
    
    def tick(self, tick):
        if World.instance.paused:
            ScriptLoader.instance.object_map["controls"].image_path = 'assets/ui/controls_pause.png'
        else: 
            ScriptLoader.instance.object_map["controls"].image_path = 'assets/ui/controls_play.png'