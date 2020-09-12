import pygame
import numpy as np
import pymunk
import pymunk.pygame_util
from ev3sim.objects.utils import magnitude_sq
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import worldspace_to_screenspace


def stop_on_pause(f):
    def new_f(*args, **kwargs):
        if World.instance.paused:
            return
        else:
            return f(*args, **kwargs)

    return new_f


class World:

    instance: "World" = None

    # Allow objects to collide 5mm before
    COLLISION_LENIENCY = 0.5

    paused = False

    def __init__(self):
        World.instance = self
        self.space = pymunk.Space()
        self.space.gravity = 0, 0
        self.objects = []

    def registerObject(self, obj):
        self.objects.append(obj)
        self.space.add(obj.body, *obj.shapes)

    def unregisterObject(self, obj):
        self.objects.remove(obj)
        self.space.remove(obj.body, *obj.shapes)

    @stop_on_pause
    def physics_tick(self, dt):
        self.space.step(dt)

    def tick(self, dt):
        self.physics_tick(dt)
        for obj in self.objects:
            obj.update()
