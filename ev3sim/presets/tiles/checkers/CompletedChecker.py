from ev3sim.presets.tiles.checkers.RescueChecker import BaseRescueChecker

class CompletedChecker(BaseRescueChecker):

    # You need 2/3 of the start and end follow points to count a tile as completed, as well as 80% of that tile.
    FOLLOW_POINT_START_END = 3
    FOLLOW_POINT_AMOUNT_REQUIRED = 2
    FOLLOW_POINT_PERCENT = 0.8

    COMPLETE_SCORE = 10

    completed = False

    def onSpawn(self):
        super().onSpawn()
        self.initial_fill = self.rescue.tiles[self.index]['ui_spawned'].children[0].visual.fill
    
    def onReset(self):
        super().onReset()
        self.rescue.tiles[self.index]['ui_spawned'].children[0].visual.fill = self.initial_fill
        self.completed = False

    @property
    def maxScore(self):
        return self.COMPLETE_SCORE

    def onNewFollowPoint(self, completed):
        if not self.completed:
            total_points = len(completed)
            total_complete = 0
            total_start = 0
            total_end = 0
            for x in range(len(completed)):
                if isinstance(completed[x], (list, tuple)):
                    for path in completed[x]:
                        path_amount = 0
                        for p in path:
                            if p:
                                path_amount += 1
                        if path_amount / len(path) >= self.FOLLOW_POINT_PERCENT:
                            # Path completed, use this one.
                            total_complete += path_amount
                            total_points += len(path) - 1
                            break
                    else:
                        # No paths complete
                        return
                elif completed[x]:
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
                self.incrementScore(self.COMPLETE_SCORE)
                self.completed = True
                print(f"Completed tile {self.index}")
