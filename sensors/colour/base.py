import random
import numpy as np

class ColourSensorMixin:

    SENSOR_RADIUS = 15
    SENSOR_POINTS = 100

    def _SenseValueAboutPosition(self, centrePosition, valueGetter):
        # Randomly sample value from SENSOR_POINTS chosen around the centrePosition.
        points = [
            random.random()*self.SENSOR_RADIUS
            for _ in range(self.SENSOR_POINTS)
        ]
        for x in range(len(points)):
            angle = random.random() * 2 * np.pi
            points[x] = valueGetter(np.array([np.cos(angle)*points[x], np.cos(angle)*points[x]]) + centrePosition)
            # For some reason the color module hangs otherwise :/
            if hasattr(points[x], 'r'):
                points[x] = np.array([points[x].r, points[x].g, points[x].b])
        total = points[0]
        for x in range(1, len(points)):
            total += points[x]
        return total / len(points)

