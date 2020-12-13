class BaseRescueChecker:
    # Does nothing.

    def __init__(self, follow_points, tileIndex, rescueController, **kwargs):
        self.follow_points = follow_points
        self.index = tileIndex
        self.rescue = rescueController

    local_score = 0

    @property
    def maxScore(self):
        return 0

    def incrementScore(self, amount):
        self.setScore(self.local_score + amount)

    def decrementScore(self, amount):
        self.setScore(self.local_score - amount)

    def setScore(self, amount, send_to_rescue=True):
        if send_to_rescue:
            self.rescue.incrementScore(amount - self.local_score)
        self.local_score = amount
        self.rescue.tiles[self.index]["ui_spawned"].children[-1].visual.text = f"{self.local_score}/{self.maxScore}"

    def onSpawn(self):
        pass

    def onReset(self):
        self.setScore(0, send_to_rescue=False)

    def onNewFollowPoint(self, completed):
        pass

    def tick(self, tick):
        pass
