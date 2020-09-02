class BaseRescueChecker:
    # Does nothing.

    def __init__(self, follow_points, tileIndex, rescueController):
        self.follow_points = follow_points
        self.index = tileIndex
        self.rescue = rescueController

    def onNewFollowPoint(self, completed):
        pass
