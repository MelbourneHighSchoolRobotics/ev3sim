import numpy as np
from ev3sim.simulation.randomisation import Randomiser


class NearestValue:
    """
    Utility class to support defaulting to the nearest value to some input, with points equidistantly separated between max and min.
    """

    def __init__(self, minimum, maximum, num_points):
        self.min = minimum
        self.max = maximum
        self.points = [self.min + i * (self.max - self.min) / (num_points - 1) for i in range(num_points)]

    def get_closest(self, val):
        # If we are on the outskirts, return boundaries
        if val <= self.points[0]:
            return self.points[0]
        if val >= self.points[-1]:
            return self.points[-1]
        # Binary search to find largest index which houses a smaller value.
        lo = 0
        hi = len(self.points)
        while hi - lo > 1:
            mid = (hi + lo) // 2
            if self.points[mid] > val:
                hi = mid
            else:
                lo = mid
        if abs(self.points[lo] - val) > abs(self.points[lo + 1] - val):
            return self.points[lo + 1]
        return self.points[lo]


class CyclicMixin:
    """
    Nearest Value, but compare points modulo some value.

    Assumes that minimum and maximum represent the same value and they are cyclic about this point.
    """

    def get_closest(self, val):
        while val < self.points[0]:
            val += self.points[-1] - self.points[0]
        while val > self.points[-1]:
            val -= self.points[-1] - self.points[0]
        # points[0] <= val <= points[-1]
        # Ensure that we don't return points[-1], handle this separately
        if abs(self.points[-2] - val) > abs(self.points[-1] - val):
            return self.points[0]
        # Binary search to find largest index which houses a smaller value.
        lo = 0
        hi = len(self.points)
        while hi - lo > 1:
            mid = (hi + lo) // 2
            if self.points[mid] > val:
                hi = mid
            else:
                lo = mid
        if abs(self.points[lo] - val) > abs(self.points[lo + 1] - val):
            return self.points[lo + 1]
        return self.points[lo]


class RandomDistributionMixin:
    def __init__(self, minimum, maximum, num_points, distribution_var, randomState):
        """Generate the points using a normal distribution"""
        super().__init__(minimum, maximum, num_points)
        # Redefine self.points
        diffs = randomState.normal(loc=0, scale=np.sqrt(distribution_var), size=(num_points - 2,))
        for x in range(num_points - 2):
            self.points[x + 1] += diffs[x]
            self.points[x + 1] = min(max(self.points[x + 1], self.min), self.max)
        self.points.sort()
