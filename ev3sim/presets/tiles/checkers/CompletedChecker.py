from ev3sim.presets.tiles.checkers.RescueChecker import BaseRescueChecker

class CompletedChecker(BaseRescueChecker):

    # You need 2/3 of the start and end follow points to count a tile as completed, as well as 80% of that tile.
    FOLLOW_POINT_START_END = 3
    FOLLOW_POINT_AMOUNT_REQUIRED = 2
    FOLLOW_POINT_PERCENT = 0.8

    def onNewFollowPoint(self, completed):
        total_complete = 0
        total_start = 0
        total_end = 0
        for x in range(len(completed)):
            if completed[x]:
                total_complete += 1
                if x < self.FOLLOW_POINT_START_END:
                    total_start += 1
                if len(completed) - x - 1 < self.FOLLOW_POINT_START_END:
                    total_end += 1
        if (
            total_complete >= self.FOLLOW_POINT_PERCENT * len(completed) and
            total_start >= self.FOLLOW_POINT_AMOUNT_REQUIRED and
            total_end >= self.FOLLOW_POINT_AMOUNT_REQUIRED
        ):
            self.rescue.tiles[self.index]['ui_spawned'].children[0].visual.fill = "#00ff00"
            print(f"Completed tile {self.index}")