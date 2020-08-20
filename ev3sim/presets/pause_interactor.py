import pygame
import pymunk
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World
from ev3sim.objects.base import DYNAMIC_CATEGORY

class PauseInteractor(IInteractor):
    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            # Toggle pause state.
            World.instance.paused = not World.instance.paused
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ DYNAMIC_CATEGORY))
            for shape in shapes:
                if shape.shape.obj.key == 'controls':
                    # Toggle pause state.
                    World.instance.paused = not World.instance.paused
    
    def tick(self, tick):
        if World.instance.paused:
            ScriptLoader.instance.object_map["controls"].visual.image_path = 'assets/ui/controls_pause.png'
        else: 
            ScriptLoader.instance.object_map["controls"].visual.image_path = 'assets/ui/controls_play.png'