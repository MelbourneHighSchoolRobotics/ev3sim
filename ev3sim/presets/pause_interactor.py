import pygame
import pymunk
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World
from ev3sim.objects.base import DYNAMIC_CATEGORY


class PauseInteractor(IInteractor):
    _pressed = False

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            # Toggle pause state.
            World.instance.paused = not World.instance.paused

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                m_pos, 0.0, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ DYNAMIC_CATEGORY)
            )
            if shapes:
                max_z = max(pq.shape.obj.clickZ for pq in shapes)
                shapes = [pq for pq in shapes if pq.shape.obj.clickZ == max_z]
            for shape in shapes:
                if shape.shape.obj.key == "controlsPause":
                    self._pressed = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                m_pos, 0.0, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ DYNAMIC_CATEGORY)
            )
            if shapes:
                max_z = max(pq.shape.obj.clickZ for pq in shapes)
                shapes = [pq for pq in shapes if pq.shape.obj.clickZ == max_z]
            for shape in shapes:
                if (shape.shape.obj.key == "controlsPause") & self._pressed:
                    # Toggle pause state.
                    World.instance.paused = not World.instance.paused
                self._pressed = False
            if len(shapes) == 0:
                self._pressed = False

    def tick(self, tick):
        if self._pressed:
            ScriptLoader.instance.object_map["controlsPause"].visual.image_path = "assets/ui/controls_pause_pressed.png"
        elif World.instance.paused:
            ScriptLoader.instance.object_map["controlsPause"].visual.image_path = "assets/ui/controls_pause_hold.png"
        else:
            ScriptLoader.instance.object_map[
                "controlsPause"
            ].visual.image_path = "assets/ui/controls_pause_released.png"
