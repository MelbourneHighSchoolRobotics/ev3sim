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
    
    def unregisterObject(self, obj: PhysicsObject):
        if obj.static:
            self.static_objects.remove(obj)
        else:
            self.objects.remove(obj)
    
    def tick(self, dt):
        for obj in self.objects:
            obj.updatePhysics(dt)
        # In order to ensure we don't have one collision completely ignore the other, first calculate velocities based on starting state.
        begin_velocity = [obj.velocity for obj in self.objects]
        accum_velocity = [np.array([0.0, 0.0]) for obj in self.objects]
        for i, obj in enumerate(self.objects):
            obj.immovable_directions = []
            for s_obj in self.static_objects:
                res = obj.collider.getCollisionInfo(s_obj.collider)
                if res['collision']:
                    # Ensure that this object then can't 'phase through' this later.
                    obj.immovable_directions.append(res['collision_vector'] / np.sqrt(magnitude_sq(res['collision_vector'])))
                    # Change velocity based on restitution (https://en.wikipedia.org/wiki/Coefficient_of_restitution)
                    accum_velocity[i] -= (1 + obj.restitution_coefficient) * res['collision_vector'] * np.dot(res['collision_vector'], begin_velocity[i]) / magnitude_sq(res['collision_vector'])
        for i, obj in enumerate(self.objects):
            for k, obj2 in enumerate(self.objects[i+1:]):
                j = i + k + 1
                res = obj.collider.getCollisionInfo(obj2.collider)
                if res['collision']:
                    # TODO: Include angular velocity in collision calculations.
                    restitution = obj.restitution_coefficient * obj2.restitution_coefficient
                    obj_velocity = np.dot(begin_velocity[i], res['collision_vector']) * res['collision_vector'] / magnitude_sq(res['collision_vector'])
                    obj2_velocity = np.dot(begin_velocity[j], res['collision_vector']) * res['collision_vector'] / magnitude_sq(res['collision_vector'])
                    m_obj = np.sqrt(magnitude_sq(obj_velocity)) * obj.mass
                    m_obj2 = np.sqrt(magnitude_sq(obj2_velocity)) * obj2.mass

                    # Change velocity based on restitution (https://en.wikipedia.org/wiki/Coefficient_of_restitution)
                    accum_velocity[i] -= obj_velocity
                    accum_velocity[i] += (obj.mass * obj_velocity + obj2.mass * obj2_velocity + obj2.mass * restitution * (obj2_velocity - obj_velocity)) / (obj.mass + obj2.mass)
                    accum_velocity[j] -= obj2_velocity
                    accum_velocity[j] += (obj.mass * obj_velocity + obj2.mass * obj2_velocity + obj.mass * restitution * (obj_velocity - obj2_velocity)) / (obj.mass + obj2.mass)

        # Apply velocities
        for i, obj in enumerate(self.objects):
            obj.velocity += accum_velocity[i]

        # Next, solve the collisions in iterations of increasing strength
        ITERATIONS = 5
        for x in range(1, ITERATIONS+1):
            strength = x / ITERATIONS
            accum_position = [np.array([0.0, 0.0]) for o in self.objects]
            for i, obj in enumerate(self.objects):
                obj.immovable_directions = []
                for s_obj in self.static_objects:
                    res = obj.collider.getCollisionInfo(s_obj.collider)
                    if res['collision']:
                        # STEP 1: Resolve collision by moving non-static object away.
                        accum_position[i] += res['collision_vector'] * strength
            for i, obj in enumerate(self.objects):
                for k, obj2 in enumerate(self.objects[i+1:]):
                    j = i + k + 1
                    res = obj.collider.getCollisionInfo(obj2.collider)
                    if res['collision']:
                        # It is assumed only one object has immovable directions which affect the calculations.
                        # Collision positions are resolved in an unweighted way (Assumes masses are equal)
                        # Otherwise this results in some cases where bots move forward where they cannot.
                        if obj.immovable_directions:
                            # We need to ensure that we don't move opposite this immovable direction.
                            result = res['collision_vector'].copy()
                            for direction in obj.immovable_directions:
                                aligned = np.dot(direction, result)
                                if aligned < 0:
                                    result -= aligned * direction
                            accum_position[i] += result * 0.5 * strength
                            accum_position[j] -= (res['collision_vector'] - result) + result * 0.5 * strength
                        elif obj2.immovable_directions:
                            # We need to ensure that we don't move opposite this immovable direction.
                            result = res['collision_vector'].copy()
                            for direction in obj2.immovable_directions:
                                aligned = np.dot(direction, result)
                                if aligned < 0:
                                    result -= aligned * direction
                            accum_position[i] += (res['collision_vector'] - result) + result * 0.5 * strength
                            accum_position[j] -= result * 0.5 * strength
                        else:
                            accum_position[i] += res['collision_vector'] * 0.5 * strength
                            accum_position[j] -= res['collision_vector'] * 0.5 * strength
            for i, obj in enumerate(self.objects):
                obj.position += accum_position[i]