import numpy as np
import pymunk
from ev3sim.objects.base import objectFactory
from ev3sim.simulation.world import World
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser


class UltrasonicSensorMixin:

    MODE_DIST_CM = "US-DIST-CM"

    device_type = "lego-sensor"
    mode = MODE_DIST_CM

    RAYCAST_RADIUS = 2
    # The max distance to look
    MAX_RAYCAST = 120
    # The maximum level of discrepancy to reality
    ACCEPTANCE_LEVEL = 1

    # 0 - 2 of actual value at max angle.
    ANGLE_RANDOM_AMPLITUDE = 40

    STATIC_RANDOM_ANGLE = np.pi / 12

    # Static offset
    OFFSET_MAX = 5

    last_angle_diff = 0

    def generateBias(self):
        self.saved = 0
        self.offset = (0.5 - self._interactor.random()) * 2 * self.OFFSET_MAX

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
            raycast = World.instance.space.segment_query_first(
                startPosition,
                endPosition,
                self.RAYCAST_RADIUS,
                pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ 0b1),
            )
            i = 0
            for obj in self.ignore_objects:
                for shape in obj.shapes:
                    shape.filter = pymunk.ShapeFilter(categories=cats[i])
                    i += 1

            if raycast == None:
                if top_length == self.MAX_RAYCAST or (not ScriptLoader.RANDOMISE_SENSORS):
                    return max(0, min(self.MAX_RAYCAST, top_length + self.offset))
                # If randomiser, linearly scale result by angle between surface normal of raycasted point.
                return max(
                    0,
                    min(
                        self.MAX_RAYCAST,
                        top_length
                        + (
                            1
                            + (self.last_angle_diff + self.STATIC_RANDOM_ANGLE * Randomiser.random())
                            * (Randomiser.random() - 0.5)
                            * self.ANGLE_RANDOM_AMPLITUDE
                            / np.pi
                            * 2
                        )
                        + self.offset,
                    ),
                )
            else:
                opposite_angle = centreRotation + np.pi
                while opposite_angle > raycast.normal.angle + np.pi:
                    opposite_angle -= 2 * np.pi
                while opposite_angle < raycast.normal.angle - np.pi:
                    opposite_angle += 2 * np.pi
                self.last_angle_diff = abs(opposite_angle - raycast.normal.angle)
            top_length = raycast.alpha * top_length - self.ACCEPTANCE_LEVEL
        return max(0, min(self.MAX_RAYCAST, self.offset))

    def _getObjName(self, port):
        return "sensor" + port

    def applyWrite(self, attribute, value):
        if attribute == "mode":
            self.mode = value
        else:
            raise ValueError(f"Unhandled write! {attribute} {value}")

    def toObject(self):
        return {
            "address": self._interactor.port,
            "driver_name": "lego-ev3-us",
            "mode": self.mode,
            "value0": self.distance_centimeters if self.mode == self.MODE_DIST_CM else self.distance_inches,
            "decimals": 0,
        }
