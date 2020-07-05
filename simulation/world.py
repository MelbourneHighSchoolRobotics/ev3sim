import pygame
import numpy as np
from objects.base import PhysicsObject
from visual.manager import ScreenObjectManager
from visual.utils import worldspace_to_screenspace

class World:

    instance: 'World' = None

    def __init__(self):
        World.instance = self
        self.objects = []
        self.static_objects = []
    
    def registerObject(self, obj: PhysicsObject):
        if obj.static:
            self.static_objects.append(obj)
        else:
            self.objects.append(obj)
    
    def tick(self, dt):
        for obj in self.objects:
            obj.updatePhysics(dt)
        for obj in self.objects:
            for s_obj in self.static_objects:
                res = obj.collider.getCollisionInfo(s_obj.collider)
                if res['collision']:
                    # STEP 1: Resolve collision by moving non-static object away.
                    obj.position += res['collision_vector']
                    # STEP 2: Change velocity based on restitution (https://en.wikipedia.org/wiki/Coefficient_of_restitution)
                    obj.velocity -= (1 + obj.restitution_coefficient) * res['collision_vector'] * np.dot(res['collision_vector'][:2], obj.velocity[:2]) / (pow(res['collision_vector'][0], 2) + pow(res['collision_vector'][1], 2))
        for i, obj in enumerate(self.objects):
            for obj2 in self.objects[i+1:]:
                res = obj.collider.getCollisionInfo(obj2.collider)
                if res['collision']:
                    restitution = obj.restitution_coefficient * obj2.restitution_coefficient
                    # STEP 1: Resolve collision by moving objects away relative to their momentum.
                    obj_velocity = np.dot(obj.velocity[:2], res['collision_vector'][:2]) * res['collision_vector'] / (pow(res['collision_vector'][0], 2) + pow(res['collision_vector'][1], 2))
                    obj2_velocity = np.dot(obj2.velocity[:2], res['collision_vector'][:2]) * res['collision_vector'] / (pow(res['collision_vector'][0], 2) + pow(res['collision_vector'][1], 2))
                    m_obj = np.sqrt(pow(obj_velocity[0], 2) + pow(obj_velocity[1], 2)) * obj.mass
                    m_obj2 = np.sqrt(pow(obj2_velocity[0], 2) + pow(obj2_velocity[1], 2)) * obj2.mass
                    obj.position += res['collision_vector'] * m_obj2 / (m_obj + m_obj2)
                    obj2.position -= res['collision_vector'] * m_obj / (m_obj + m_obj2)
                    # STEP 2: Change velocity based on restitution (https://en.wikipedia.org/wiki/Coefficient_of_restitution)
                    obj.velocity -= obj_velocity
                    obj.velocity += (obj.mass * obj_velocity + obj2.mass * obj2_velocity + obj2.mass * restitution * (obj2_velocity - obj_velocity)) / (obj.mass + obj2.mass)
                    obj2.velocity -= obj2_velocity
                    obj2.velocity += (obj.mass * obj_velocity + obj2.mass * obj2_velocity + obj.mass * restitution * (obj_velocity - obj2_velocity)) / (obj.mass + obj2.mass)
