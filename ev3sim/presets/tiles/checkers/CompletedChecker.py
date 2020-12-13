from ev3sim.presets.tiles.checkers.RescueChecker import BaseRescueChecker


class CompletedChecker(BaseRescueChecker):

    # You need 4/5 of the start and end follow points to count a tile as completed, as well as 80% of that tile.
    FOLLOW_POINT_START_END = 5
    FOLLOW_POINT_AMOUNT_REQUIRED = 4
    FOLLOW_POINT_PERCENT = 0.8

    COMPLETE_SCORE = 10

    completed = False

    def onSpawn(self):
        super().onSpawn()
        self.initial_fill = self.rescue.tiles[self.index]["ui_spawned"].children[0].visual.fill

    def onReset(self):
        super().onReset()
        self.rescue.tiles[self.index]["ui_spawned"].children[0].visual.fill = self.initial_fill
        self.completed = False

    @property
    def maxScore(self):
        return self.COMPLETE_SCORE

    def onNewFollowPoint(self, completed):
        if not self.completed:
            total_points = len(completed)
            total_complete = 0
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
            total_start = 0
            points_seen = 0
            for x in range(len(completed)):
                if isinstance(completed[x], (list, tuple)):
                    best_completed = total_start
                    path_index = -1
                    for y, path in enumerate(completed[x]):
                        saved_points = points_seen
                        saved_completed = total_start
                        for p in path:
                            saved_points += 1
                            saved_completed += p
                            if saved_points >= self.FOLLOW_POINT_START_END:
                                break
                        if best_completed <= saved_completed:
                            best_completed = saved_completed
                            path_index = y
                    total_start = best_completed
                    points_seen += len(completed[x][path_index])
                else:
                    points_seen += 1
                    if completed[x]:
                        total_start += 1
                if points_seen >= self.FOLLOW_POINT_START_END:
                    break
            total_end = 0
            points_seen = 0
            for x in range(len(completed) - 1, -1, -1):
                if isinstance(completed[x], (list, tuple)):
                    best_completed = total_end
                    path_index = -1
                    for y, path in enumerate(completed[x]):
                        saved_points = points_seen
                        saved_completed = total_end
                        for p in path[::-1]:
                            saved_points += 1
                            saved_completed += p
                            if saved_points >= self.FOLLOW_POINT_START_END:
                                break
                        if best_completed <= saved_completed:
                            best_completed = saved_completed
                            path_index = y
                    total_end = best_completed
                    points_seen += len(completed[x][path_index])
                else:
                    points_seen += 1
                    if completed[x]:
                        total_end += 1
                if points_seen >= self.FOLLOW_POINT_START_END:
                    break
            if (
                total_complete >= self.FOLLOW_POINT_PERCENT * len(completed)
                and total_start >= self.FOLLOW_POINT_AMOUNT_REQUIRED
                and total_end >= self.FOLLOW_POINT_AMOUNT_REQUIRED
            ):
                self.rescue.tiles[self.index]["ui_spawned"].children[0].visual.fill = "#00ff00"
                self.incrementScore(self.COMPLETE_SCORE)
                self.completed = True
                print(f"Completed tile {self.index}")
