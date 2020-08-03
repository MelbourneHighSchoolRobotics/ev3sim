import numpy as np
import pymunk
from objects.base import objectFactory
from simulation.world import World

class UltrasonicSensorMixin:

    RAYCAST_RADIUS = 2
    # The max distance to look
    MAX_RAYCAST = 120
    # The maximum level of discrepancy to reality
    ACCEPTANCE_LEVEL = 1

    def _SetIgnoredObjects(self, objs):
        self.ignore_objects = objs

    def _DistanceFromSensor(self, startPosition, centreRotation):
        top_length = self.MAX_RAYCAST
        while top_length > 0:
            endPosition = startPosition + top_length * np.array([np.cos(centreRotation), np.sin(centreRotation)])
            # Ignore all ignored objects by setting the category on them.
            for obj in self.ignore_objects:
                obj.shape.filter = pymunk.ShapeFilter(categories=0b1)
            raycast = World.instance.space.segment_query_first(startPosition, endPosition, self.RAYCAST_RADIUS, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ 0b1))
            for obj in self.ignore_objects:
                # TODO: Change me.
                obj.shape.filter = pymunk.ShapeFilter(categories=pymunk.ShapeFilter.ALL_CATEGORIES)

            if raycast == None:
                return top_length
            top_length = raycast.alpha * top_length - self.ACCEPTANCE_LEVEL
        return 0                
