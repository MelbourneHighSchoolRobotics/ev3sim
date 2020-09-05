class NearestValue:
    """
    Utility class to support defaulting to the nearest value to some input, with points equidistantly separated between max and min.
    """

    def __init__(self, minimum, maximum, num_points):
        self.min = minimum
        self.max = maximum
        self.points = [
            self.min + i * (self.max - self.min) / (num_points - 1)
            for i in range(num_points)
        ]

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
        if abs(self.points[lo] - val) > abs(self.points[lo+1] - val):
            return self.points[lo+1]
        return self.points[lo]