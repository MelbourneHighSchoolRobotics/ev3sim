import pygame
import numpy as np
from objects.base import PhysicsObject
from objects.utils import magnitude_sq
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
            obj.immovable_directions = []
            for s_obj in self.static_objects:
                res = obj.collider.getCollisionInfo(s_obj.collider)
                if res['collision']:
                    # STEP 1: Resolve collision by moving non-static object away.
                    obj.position += res['collision_vector']
                    # Ensure that this object then can't 'phase through' this later.
                    obj.immovable_directions.append(res['collision_vector'] / np.sqrt(magnitude_sq(res['collision_vector'])))
                    # STEP 2: Change velocity based on restitution (https://en.wikipedia.org/wiki/Coefficient_of_restitution)
                    obj.velocity -= (1 + obj.restitution_coefficient) * res['collision_vector'] * np.dot(res['collision_vector'], obj.velocity) / magnitude_sq(res['collision_vector'])
        for i, obj in enumerate(self.objects):
            for obj2 in self.objects[i+1:]:
                res = obj.collider.getCollisionInfo(obj2.collider)
                if res['collision']:
                    restitution = obj.restitution_coefficient * obj2.restitution_coefficient
                    # STEP 1: Resolve collision by moving objects away relative to their momentum.
                    obj_velocity = np.dot(obj.velocity, res['collision_vector']) * res['collision_vector'] / magnitude_sq(res['collision_vector'])
                    obj2_velocity = np.dot(obj2.velocity, res['collision_vector']) * res['collision_vector'] / magnitude_sq(res['collision_vector'])
                    m_obj = np.sqrt(magnitude_sq(obj_velocity)) * obj.mass
                    m_obj2 = np.sqrt(magnitude_sq(obj2_velocity)) * obj2.mass

                    # It is assumed only one object has immovable directions which affect the calculations.
                    if obj.immovable_directions:
                        # We need to ensure that we don't move opposite this immovable direction.
                        result = res['collision_vector'].copy()
                        for direction in obj.immovable_directions:
                            aligned = np.dot(direction, result)
                            if aligned < 0:
                                result -= aligned * direction
                        obj.position += result * m_obj2 / (m_obj + m_obj2)
                        obj2.position -= (res['collision_vector'] - result) + result * m_obj / (m_obj + m_obj2)
                    elif obj2.immovable_directions:
                        # We need to ensure that we don't move opposite this immovable direction.
                        result = res['collision_vector'].copy()
                        for direction in obj2.immovable_directions:
                            aligned = np.dot(direction, result)
                            if aligned < 0:
                                result -= aligned * direction
                        obj.position += (res['collision_vector'] - result) + result * m_obj2 / (m_obj + m_obj2)
                        obj2.position -= result * m_obj / (m_obj + m_obj2)
                    else:
                        obj.position += res['collision_vector'] * m_obj2 / (m_obj + m_obj2)
                        obj2.position -= res['collision_vector'] * m_obj / (m_obj + m_obj2)
                    # STEP 2: Change velocity based on restitution (https://en.wikipedia.org/wiki/Coefficient_of_restitution)
                    obj.velocity -= obj_velocity
                    obj.velocity += (obj.mass * obj_velocity + obj2.mass * obj2_velocity + obj2.mass * restitution * (obj2_velocity - obj_velocity)) / (obj.mass + obj2.mass)
                    obj2.velocity -= obj2_velocity
                    obj2.velocity += (obj.mass * obj_velocity + obj2.mass * obj2_velocity + obj.mass * restitution * (obj_velocity - obj2_velocity)) / (obj.mass + obj2.mass)
