import numpy as np
import pymunk
from ev3sim.objects.base import objectFactory
from ev3sim.simulation.world import World

class UltrasonicSensorMixin:

    MODE_DIST_CM = 'US-DIST-CM'

    device_type = 'lego-sensor'
    mode = MODE_DIST_CM

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
            cats = []
            for obj in self.ignore_objects:
                for shape in obj.shapes:
                    cats.append(shape.filter.categories)
                    shape.filter = pymunk.ShapeFilter(categories=0b1)
            raycast = World.instance.space.segment_query_first(startPosition, endPosition, self.RAYCAST_RADIUS, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ 0b1))
            i = 0
            for obj in self.ignore_objects:
                for shape in obj.shapes:
                    shape.filter = pymunk.ShapeFilter(categories=cats[i])
                    i += 1

            if raycast == None:
                return top_length
            top_length = raycast.alpha * top_length - self.ACCEPTANCE_LEVEL
        return 0                

    def _getObjName(self, port):
        return 'sensor' + port

    def applyWrite(self, attribute, value):
        if attribute == 'mode':
            self.mode = value
        else:
            raise ValueError(f'Unhandled write! {attribute} {value}')

    def toObject(self):
        return {
            'address': self._interactor.port,
            'driver_name': 'lego-ev3-us',
            'mode': self.mode,
            'value0': self.distance_centimeters if self.mode == self.MODE_DIST_CM else self.distance_inches,
            'decimals': 0,
        }