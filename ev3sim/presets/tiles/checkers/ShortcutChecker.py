from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.objects.base import objectFactory
from ev3sim.presets.tiles.checkers.CompletedChecker import CompletedChecker


class ShortcutChecker(CompletedChecker):

    SHORTCUT_SCORE = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These are tuples of length 3 containing 3 values:
        # - The index of the branch (IE the first path branch is index 0)
        # - The index of the path in that branch (IE the shortcut is to take the 2nd path)
        # - Whether this shortcut awards points on 'enter' or 'exit'.
        self.shortcuts = kwargs.get("shortcut_paths")
        self.shortcut_complete = [False for s in self.shortcuts]
        for shortcut in self.shortcuts:
            assert shortcut[2] in (
                "enter",
                "exit",
            ), f"Invalid shortcut third value: {shortcut[2]} should be 'enter' or 'exit'"

    def onSpawn(self):
        super().onSpawn()
        # This is a rectangle which will contain the completion rects.
        bounding = self.rescue.tiles[self.index]["ui_spawned"].children[1]
        self.original_fill = bounding.visual.fill
        completion_rect_args = [
            {
                "type": "object",
                "physics": False,
                "visual": {
                    "name": "Rectangle",
                    "width": bounding.visual.width,
                    "height": bounding.visual.height / len(self.shortcuts),
                    "fill": self.original_fill,
                    "stroke": "#000000",
                    "stroke_width": 0,
                    "zPos": 5.5,
                },
                "position": [0, ((len(self.shortcuts) - 1) / 2 - x) * bounding.visual.height / len(self.shortcuts)],
            }
            for x in range(len(self.shortcuts))
        ]
        cur_length = len(bounding.children)
        self.completion_rects = []
        for i, child in enumerate(completion_rect_args):
            child["key"] = bounding.key + f"-child-{i+cur_length}"
            bounding.children.append(objectFactory(**child))
            self.completion_rects.append(bounding.children[-1])
            ScreenObjectManager.instance.registerObject(bounding.children[-1], bounding.children[-1].key)
            bounding.children[-1].parent = bounding
        bounding.updateVisualProperties()

    def onReset(self):
        super().onReset()
        self.shortcut_complete = [False for s in self.shortcuts]
        for rect in self.completion_rects:
            rect.visual.fill = self.original_fill

    @property
    def maxScore(self):
        return super().maxScore + len(self.shortcuts) * self.SHORTCUT_SCORE

    # Check 5 points either side of shortcut
    PATH_CHECK_POINTS = 5
    # Ensure 4 of these points are complete.
    PATH_COMPLETION_PCT = 0.8

    def onNewFollowPoint(self, completed):
        super().onNewFollowPoint(completed)
        for a, shortcut in enumerate(self.shortcuts):
            if self.shortcut_complete[a]:
                continue
            # First find the index of the shortcut
            path_index = -1
            path_location = -1
            for x in range(len(completed)):
                if isinstance(completed[x], (list, tuple)):
                    path_index += 1
                if path_index == shortcut[0]:
                    path_location = x
                    break
            else:
                raise ValueError(f"Expected {shortcut[0] + 1} branches in tile but found {path_index + 1}")
            if shortcut[2] == "enter":
                # Check that we've entered this path correctly.
                points = completed[path_location][shortcut[1]][: self.PATH_CHECK_POINTS]
                enter_good = sum(points) / len(points) >= self.PATH_COMPLETION_PCT
                pre_path_points = completed[max(path_location - self.PATH_CHECK_POINTS, 0) : path_location]
                # Ensure no extra branches are in pre_path_points
                while True:
                    for x, point in enumerate(pre_path_points):
                        if isinstance(point, (list, tuple)):
                            pre_path_points = pre_path_points[x + 1 :]
                            break
                    else:
                        break
                pre_good = sum(pre_path_points) / len(pre_path_points) >= self.PATH_COMPLETION_PCT
                if enter_good and pre_good:
                    self.shortcut_complete[a] = True
                    self.completion_rects[a].visual.fill = "#00ff00"
                    self.incrementScore(self.SHORTCUT_SCORE)
            elif shortcut[2] == "exit":
                # Check that we've exited this path correctly.
                points = completed[path_location][shortcut[1]][-self.PATH_CHECK_POINTS :]
                enter_good = sum(points) / len(points) >= self.PATH_COMPLETION_PCT
                post_path_points = completed[
                    path_location + 1 : min(path_location + self.PATH_CHECK_POINTS + 1, len(completed))
                ]
                # Ensure no extra branches are in post_path_points
                while True:
                    for x, point in enumerate(post_path_points):
                        if isinstance(point, (list, tuple)):
                            post_path_points = post_path_points[:x]
                            break
                    else:
                        break
                post_good = sum(post_path_points) / len(post_path_points) >= self.PATH_COMPLETION_PCT
                if enter_good and post_good:
                    self.shortcut_complete[a] = True
                    self.completion_rects[a].visual.fill = "#00ff00"
                    self.incrementScore(self.SHORTCUT_SCORE)
