import pygame
import pymunk
from ev3sim.devices.base import Device, IDeviceInteractor
from ev3sim.devices.button.base import ButtonMixin
from ev3sim.objects.base import DYNAMIC_CATEGORY
from ev3sim.simulation.world import World
from ev3sim.visual.utils import screenspace_to_worldspace


class ButtonInteractor(IDeviceInteractor):

    name = "BUTTON"

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=DYNAMIC_CATEGORY))
            if shapes:
                max_z = max(pq.shape.obj.clickZ for pq in shapes)
                shapes = [pq for pq in shapes if pq.shape.obj.clickZ == max_z]
                for pq in shapes:
                    if pq.shape.obj.key == self.generated[0].key:
                        self.device_class.pressed = True
                        self.generated[0].visual.fill = "BUTTON_back_color_press"
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.device_class.pressed = False
            self.generated[0].visual.fill = "BUTTON_back_color_release"


class Button(ButtonMixin, Device):
    pass
