import numpy as np
from objects.base import objectFactory
from simulation.world import World

class UltrasonicSensorMixin:

    RAYCAST_WIDTH = 2
    # The max distance to look
    MAX_RAYCAST = 120
    # The maximum level of discrepancy to reality
    ACCEPTANCE_LEVEL = 1

    def _InitialiseRaycast(self):
        self.raycast = objectFactory(**{
            'visual': {
                'name': 'Rectangle',
                'height': self.RAYCAST_WIDTH / 2,
                'width': 10,
                'fill': '#ff0000',
                'stroke': None,
            },
            'collider': 'inherit',
            'physics': True,
            'position': [0, 0]
        })

    def _SetIgnoredObjects(self, objs):
        self.ignore_objects = list(map(lambda x: x.key, objs))

    def _GenerateRaycast(self, centrePosition, centreRotation, distance):
        self.raycast.visual.initFromKwargs(**{
            'height': self.RAYCAST_WIDTH / 2,
            'width': distance,
            'fill': '#ff0000',
            'stroke': None,
        })
        self.raycast.rotation = centreRotation
        self.raycast.position = centrePosition + distance / 2 * np.array([np.cos(centreRotation), np.sin(centreRotation)])
        self.raycast.collider = self.raycast.visual.generateCollider(self.raycast)
        return self.raycast

    def _DistanceFromSensor(self, centrePosition, centreRotation):
        # We raycast max length, continuously move back to intersection point.
        length = self.MAX_RAYCAST + 0.01
        while True:
            rect = self._GenerateRaycast(centrePosition, centreRotation, length)
            # Look for collisions
            collided = False
            shortest_collision_length = length + 2 * self.ACCEPTANCE_LEVEL
            for obj in World.instance.objects + World.instance.static_objects:
                if obj.key in self.ignore_objects: continue
                info = obj.collider.getCollisionInfo(rect.collider)
                if info['collision']:
                    collided = True
                    test = np.dot(info['world_space_position'] - centrePosition, np.array([np.cos(centreRotation), np.sin(centreRotation)]))
                    if test > 0:
                        shortest_collision_length = min(test, shortest_collision_length)
            if collided:
                if shortest_collision_length - length > self.ACCEPTANCE_LEVEL: break
                length = shortest_collision_length - self.ACCEPTANCE_LEVEL
            else:
                break
        return length
                
