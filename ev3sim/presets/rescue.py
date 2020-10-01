import datetime
import numpy as np
import math
import pymunk
import pygame
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory, STATIC_CATEGORY
from ev3sim.objects.utils import local_space_to_world_space, magnitude_sq
from ev3sim.file_helper import find_abs
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace


class RescueInteractor(IInteractor):

    FOLLOW_POINT_CATEGORY = 0b1000
    SHOW_FOLLOW_POINTS = True
    SHOW_ROBOT_COLLIDER = False
    FOLLOW_POINT_COLLISION_TYPE = 5
    ROBOT_CENTRE_COLLISION_TYPE = 6
    ROBOT_CENTRE_RADIUS = 3
    FOLLOW_POINT_RADIUS = 1
    # You can be at most this far from the previous follow point before lack of progress is called.
    MAX_FOLLOW_DIST = 8
    # Randomisation constants
    BOT_SPAWN_RADIUS = 2
    BOT_SPAWN_ANGLE = [-10, 10]

    START_TIME = datetime.timedelta(minutes=5)

    TILE_LENGTH = 30
    _pressed = False
    _touches = 0
    _touch_points = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawns = kwargs.get("spawns")
        self.time_tick = 0
        self.tiles = []
        for i, tile in enumerate(kwargs["tiles"]):
            self.tiles.append({})
            import yaml

            path = find_abs(tile["path"], allowed_areas=["local/presets/", "local", "package/presets/", "package"])
            with open(path, "r") as f:
                t = yaml.safe_load(f)
            self.maxZpos = 0
            base_pos = np.array(tile.get("position", [0, 0]))
            # Transfer to rescue space.
            base_pos = [base_pos[0] * self.TILE_LENGTH, base_pos[1] * self.TILE_LENGTH]
            base_rotation = tile.get("rotation", 0) * np.pi / 180
            flip = tile.get("flip", False)
            for obj in t["elements"]:
                rel_pos = np.array(obj.get("position", [0, 0]))
                if flip:
                    rel_pos[0] = -rel_pos[0]
                    if obj.get("name", "") == "Image":
                        obj["flip"] = [True, False]
                obj["rotation"] = (obj.get("rotation", 0)) * np.pi / 180 + base_rotation
                obj["position"] = local_space_to_world_space(rel_pos, base_rotation, base_pos)
                obj["sensorVisible"] = True
                k = obj["key"]
                obj["key"] = f"Tile-{i}-{k}"
                self.maxZpos = max(self.maxZpos, obj.get("zPos", 0))
            t["elements"].append(
                {
                    "position": local_space_to_world_space(np.array([0, 0]), base_rotation, base_pos),
                    "rotation": base_rotation,
                    "type": "visual",
                    "name": "Rectangle",
                    "width": self.TILE_LENGTH,
                    "height": self.TILE_LENGTH,
                    "fill": None,
                    "stroke_width": 0.1,
                    "stroke": "rescue_outline_color",
                    "zPos": self.maxZpos + 0.1,
                    "key": f"Tile-{i}-outline",
                    "sensorVisible": False,
                }
            )
            self.tiles[-1]["follows"] = []
            self.tiles[-1]["roam_status"] = []
            self.tiles[-1]["world_pos"] = base_pos
            self.tiles[-1]["rotation"] = base_rotation
            mname, cname = t.get("checker").rsplit(".", 1)
            import importlib

            klass = getattr(importlib.import_module(mname), cname)
            with open(
                find_abs(t["ui"], allowed_areas=["local/presets/", "local", "package/presets/", "package"]), "r"
            ) as f:
                self.tiles[-1]["ui_elem"] = yaml.safe_load(f)
            for j, point in enumerate(t["follow_points"]):
                if isinstance(point[0], (list, tuple)):
                    self.tiles[-1]["follows"].append([])
                    self.tiles[-1]["roam_status"].append([])
                    for path in point:
                        self.tiles[-1]["follows"][-1].append([])
                        self.tiles[-1]["roam_status"][-1].append([])
                        for point2 in path:
                            if isinstance(point2, str):
                                self.tiles[-1]["roam_status"][-1][-1][-1] = point2
                            else:
                                if flip:
                                    point2[0] = -point2[0]
                                self.tiles[-1]["follows"][-1][-1].append(
                                    local_space_to_world_space(
                                        np.array(point2), tile.get("rotation", 0) * np.pi / 180, base_pos
                                    )
                                )
                                self.tiles[-1]["roam_status"][-1][-1].append(None)
                else:
                    if isinstance(point, str):
                        self.tiles[-1]["roam_status"][-1] = point
                    else:
                        if flip:
                            point[0] = -point[0]
                        self.tiles[-1]["follows"].append(
                            local_space_to_world_space(np.array(point), tile.get("rotation", 0) * np.pi / 180, base_pos)
                        )
                        self.tiles[-1]["roam_status"].append(None)
            self.tiles[-1]["checker"] = klass(self.tiles[-1]["follows"], i, self, **t.get("checker_kwargs", {}))
            self.tiles[-1]["all_elems"] = ScriptLoader.instance.loadElements(t["elements"])

    def _recurseObj(self, obj, indicies):
        for index in indicies:
            obj = obj[index]
        return obj

    def lackOfProgress(self, bot_index):
        print("Lack of Progress!")
        World.instance.paused = True
        self.current_follow = None

    def collidedFollowPoint(self, follow_indexes, bot_index):
        if self._recurseObj(self.follow_completed[follow_indexes[0]], follow_indexes[1:]):
            return
        roam = self._recurseObj(self.tiles[follow_indexes[0]]["roam_status"], follow_indexes[1:])
        if roam is not None:
            if roam == "ROAM_START":
                self.roaming[bot_index] = (True, follow_indexes[1:])
                self.roam_tile[bot_index] = follow_indexes[0]
            if roam == "ROAM_END":
                self.roaming[bot_index] = False
        else:
            if (
                self.roaming[bot_index]
                and follow_indexes[1:] > self.roaming[bot_index][1]
                and follow_indexes[0] == self.roam_tile[bot_index]
            ):
                # We should hit the roam end trigger first.
                self.lackOfProgress(bot_index)
        self.current_follow = follow_indexes
        self._recurseObj(self.follow_completed[follow_indexes[0]], follow_indexes[1:-1])[follow_indexes[-1]] = True
        self._recurseObj(self.tiles[follow_indexes[0]]["follow_colliders"], follow_indexes[1:]).visual.fill = "#00ff00"
        self.tiles[follow_indexes[0]]["checker"].onNewFollowPoint(self.follow_completed[follow_indexes[0]])

    def follow_point_colour(self, indicies):
        return (
            "#ff0000" if self._recurseObj(self.tiles[indicies[0]]["roam_status"], indicies[1:]) is None else "#0000ff"
        )

    def _spawnFollowAtLocationWithIndicies(self, position, indicies):
        key = "Tile-follow-" + "-".join(list(map(str, indicies)))
        obj = objectFactory(
            **{
                "collider": "inherit",
                "visual": {
                    "name": "Circle",
                    "radius": self.FOLLOW_POINT_RADIUS,
                    "fill": self.follow_point_colour(indicies) if self.SHOW_FOLLOW_POINTS else None,
                    "stroke_width": 0,
                    "sensorVisible": False,
                    "zPos": self.maxZpos + 0.2,
                },
                "position": position,
                "physics": True,
                "static": True,
                "key": key,
            }
        )
        obj.shape.filter = pymunk.ShapeFilter(categories=self.FOLLOW_POINT_CATEGORY)
        obj.shape.sensor = True
        obj.shape._follow_indexes = indicies
        obj.shape.collision_type = self.FOLLOW_POINT_COLLISION_TYPE
        World.instance.registerObject(obj)
        if self.SHOW_FOLLOW_POINTS:
            ScreenObjectManager.instance.registerObject(obj, obj.key)
        return obj

    def spawnFollowPointPhysics(self):
        for i, tile in enumerate(self.tiles):
            tile["follow_colliders"] = []
            for j, pos in enumerate(tile["follows"]):
                if isinstance(pos[0], (list, tuple)):
                    tile["follow_colliders"].append([])
                    for k, path in enumerate(pos):
                        tile["follow_colliders"][-1].append([])
                        for l, pos2 in enumerate(path):
                            obj = self._spawnFollowAtLocationWithIndicies(pos2, (i, j, k, l))
                            tile["follow_colliders"][-1][-1].append(obj)
                else:
                    obj = self._spawnFollowAtLocationWithIndicies(pos, (i, j))
                    tile["follow_colliders"].append(obj)

    TILE_UI_ELEM_HEIGHT = 10
    TILE_UI_PADDING = 20
    TILE_UI_INITIAL_HEIGHT = 98

    @property
    def tileUIHeight(self):
        return self.TILE_UI_PADDING * 2 + self.TILE_UI_ELEM_HEIGHT * len(self.tiles)

    def spawnTileUI(self):
        elems = []
        for i, tile in enumerate(self.tiles):
            elem = tile["ui_elem"]
            elem["key"] = f"Tile-{i}-UI"
            elem["position"] = [-140, -self.TILE_UI_ELEM_HEIGHT * (i - (len(self.tiles) - 1) / 2)]
            elems.append(elem)
        for i, spawned in enumerate(ScriptLoader.instance.loadElements(elems)):
            self.tiles[i]["ui_spawned"] = spawned
            self.tiles[i]["checker"].onSpawn()
        ScriptLoader.instance.object_map["rescueBGMid"].scale = (1, self.tileUIHeight / self.TILE_UI_INITIAL_HEIGHT)
        ScriptLoader.instance.object_map["rescueBGTop"].position = (-146.6, self.tileUIHeight / 2)
        ScriptLoader.instance.object_map["rescueBGBottom"].position = (-146.6, -self.tileUIHeight / 2)
        ScriptLoader.instance.object_map["rescueScoreSum"].position = (
            -110,
            -self.tileUIHeight / 2 + self.TILE_UI_PADDING / 2,
        )
        ScriptLoader.instance.object_map["touchesTitle"].position = (
            ScriptLoader.instance.object_map["touchesTitle"].position[0],
            self.tileUIHeight / 2 - self.TILE_UI_PADDING / 2,
        )
        ScriptLoader.instance.object_map["touchesCount"].position = (
            ScriptLoader.instance.object_map["touchesCount"].position[0],
            self.tileUIHeight / 2 - self.TILE_UI_PADDING / 2,
        )
        ScriptLoader.instance.object_map["touchesScore"].position = (
            ScriptLoader.instance.object_map["touchesScore"].position[0],
            self.tileUIHeight / 2 - self.TILE_UI_PADDING / 2,
        )
        self.touchesChanged()

    def locateBots(self):
        self.robots = []
        self.bot_follows = []
        bot_index = 0
        while True:
            # Find the next robot.
            possible_keys = []
            for key in ScriptLoader.instance.object_map.keys():
                if key.startswith(f"Robot-{bot_index}"):
                    possible_keys.append(key)
            if len(possible_keys) == 0:
                break
            possible_keys.sort(key=len)
            self.robots.append(ScriptLoader.instance.object_map[possible_keys[0]])
            # Spawn the robot follow point collider.
            obj = objectFactory(
                **{
                    "collider": "inherit",
                    "visual": {
                        "name": "Circle",
                        "radius": self.ROBOT_CENTRE_RADIUS,
                        "fill": "#00ff00" if self.SHOW_ROBOT_COLLIDER else None,
                        "stroke_width": 0,
                        "sensorVisible": False,
                        "zPos": 100,
                    },
                    "physics": True,
                    "key": f"Robot-{bot_index}-follow",
                }
            )
            obj.shape.sensor = True
            obj.shape.collision_type = self.ROBOT_CENTRE_COLLISION_TYPE
            obj.shape._robot_index = bot_index
            World.instance.registerObject(obj)
            if self.SHOW_ROBOT_COLLIDER:
                ScreenObjectManager.instance.registerObject(obj, obj.key)
            self.bot_follows.append(obj)
            bot_index += 1

        if len(self.robots) == 0:
            raise ValueError("No robots loaded.")

    def startUp(self):
        self.spawnFollowPointPhysics()
        self.spawnTileUI()
        self.locateBots()
        assert len(self.robots) <= len(self.spawns), "Not enough spawning locations specified."
        self.scores = [0] * len(self.robots)

        self.reset()
        for i in range(len(self.robots)):
            # This is bad, I should get the robot key somehow else (Generally speaking the robot class, interactor and object should be more tightly coupled.)
            self.bot_follows[i].body.position = local_space_to_world_space(
                ScriptLoader.instance.robots[f"Robot-{i}"]._follow_collider_offset,
                self.robots[i].body.angle,
                (self.robots[i].body.position.x, self.robots[i].body.position.y),
            )
        self.addCollisionHandler()

        for robot in self.robots:
            robot.robot_class.onSpawn()

    def addCollisionHandler(self):
        handler = World.instance.space.add_collision_handler(
            self.FOLLOW_POINT_COLLISION_TYPE, self.ROBOT_CENTRE_COLLISION_TYPE
        )

        def handle_collide(arbiter, space, data):
            a, b = arbiter.shapes
            if hasattr(a, "_follow_indexes"):
                self.collidedFollowPoint(a._follow_indexes, b._robot_index)
            elif hasattr(b, "_follow_indexes"):
                self.collidedFollowPoint(b._follow_indexes, a._robot_index)
            else:
                raise ValueError("Two objects with collision types used by rescue don't have a tile follow point.")
            return False

        handler.begin = handle_collide

    def spawnAt(self, tileIndex):
        self.resetFollows()
        spawn_point = self.tiles[tileIndex]["follows"][0]
        for i in range(len(self.robots)):
            self.robots[i].body.angle = self.tiles[tileIndex]["rotation"]
            self.bot_follows[i].body.position = local_space_to_world_space(
                ScriptLoader.instance.robots[f"Robot-{i}"]._follow_collider_offset,
                self.robots[i].body.angle,
                (self.robots[i].body.position.x, self.robots[i].body.position.y),
            )
            self.robots[i].body.position += spawn_point - self.bot_follows[i].body.position
            self.robots[i].body.velocity = (0, 0)
            self.robots[i].body.angular_velocity = 0
        self.touchBot()

    def resetFollows(self):
        self.current_follow = None
        self.follow_completed = [
            [[[False for point in path] for path in x] if isinstance(x, (list, tuple)) else False for x in y["follows"]]
            for y in self.tiles
        ]
        for x in range(len(self.tiles)):
            for y in range(len(self.tiles[x]["follow_colliders"])):
                if isinstance(self.tiles[x]["follow_colliders"][y], (list, tuple)):
                    for z, path in enumerate(self.tiles[x]["follow_colliders"][y]):
                        for w in range(len(path)):
                            path[w].visual.fill = self.follow_point_colour((x, y, z, w))
                else:
                    self.tiles[x]["follow_colliders"][y].visual.fill = self.follow_point_colour((x, y))
        self.roaming = [False] * len(self.robots)
        self.roam_tile = [-1] * len(self.robots)

    def reset(self):
        self.resetPositions()
        self.time_tick = 0
        self._touches = 0
        self._touch_points = 0
        self.touchesChanged()
        self.setScore(0)
        self.resetFollows()
        for x in range(len(self.tiles)):
            self.tiles[x]["checker"].onReset()

    def setScore(self, val):
        self.score = val
        ScriptLoader.instance.object_map["rescueScoreSum"].text = str(self.score)

    def incrementScore(self, val):
        self.setScore(self.score + val)

    def decrementScore(self, val):
        self.setScore(self.score - val)

    def resetPositions(self):
        for i, robot in enumerate(self.robots):
            diff_radius = Randomiser.random() * self.BOT_SPAWN_RADIUS
            diff_angle = Randomiser.random() * 2 * np.pi
            robot.body.position = np.array(
                [self.spawns[i][0][0] * self.TILE_LENGTH, self.spawns[i][0][1] * self.TILE_LENGTH]
            ) + diff_radius * np.array([np.cos(diff_angle), np.sin(diff_angle)])
            robot.body.angle = (
                (
                    self.spawns[i][1]
                    + self.BOT_SPAWN_ANGLE[0]
                    + Randomiser.random() * (self.BOT_SPAWN_ANGLE[1] - self.BOT_SPAWN_ANGLE[0])
                )
                * np.pi
                / 180
            )
            robot.body.velocity = np.array([0.0, 0.0])
            robot.body.angular_velocity = 0

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
        for i in range(len(self.robots)):
            self.bot_follows[i].body.position = local_space_to_world_space(
                ScriptLoader.instance.robots[f"Robot-{i}"]._follow_collider_offset,
                self.robots[i].body.angle,
                (self.robots[i].body.position.x, self.robots[i].body.position.y),
            )
            # Ensure visual is not 1 frame behind.
            self.bot_follows[i].position = local_space_to_world_space(
                ScriptLoader.instance.robots[f"Robot-{i}"]._follow_collider_offset,
                self.robots[i].body.angle,
                (self.robots[i].body.position.x, self.robots[i].body.position.y),
            )
            if self.current_follow is not None and not World.instance.paused:
                distance = magnitude_sq(
                    self.bot_follows[i].position
                    - self._recurseObj(self.tiles[self.current_follow[0]]["follows"], self.current_follow[1:])
                )
                if distance > self.MAX_FOLLOW_DIST * self.MAX_FOLLOW_DIST and not self.roaming[i]:
                    self.lackOfProgress(i)
            if self.roaming[i] and not World.instance.paused:
                # Check we are still in the tile. Kinda bad.
                if (
                    abs(self.bot_follows[i].position[0] - self.tiles[self.roam_tile[i]]["world_pos"][0])
                    > self.TILE_LENGTH / 2
                    or abs(self.bot_follows[i].position[1] - self.tiles[self.roam_tile[i]]["world_pos"][1])
                    > self.TILE_LENGTH / 2
                ) and magnitude_sq(
                    self.bot_follows[i].position
                    - self._recurseObj(self.tiles[self.roam_tile[i]]["follows"], self.roaming[i][1])
                ) > (
                    self.ROBOT_CENTRE_RADIUS + self.FOLLOW_POINT_RADIUS + 0.05
                ) * (
                    self.ROBOT_CENTRE_RADIUS + self.FOLLOW_POINT_RADIUS + 0.05
                ):
                    self.lackOfProgress(i)
        for i in range(len(self.tiles)):
            self.tiles[i]["checker"].tick(tick)
        # UI Tick
        if self._pressed:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "assets/ui/controls_reset_pressed.png"
        else:
            ScriptLoader.instance.object_map[
                "controlsReset"
            ].visual.image_path = "assets/ui/controls_reset_released.png"
        self.update_time()

    @stop_on_pause
    def update_time(self):
        self.time_tick += 1
        elapsed = datetime.timedelta(seconds=self.time_tick / ScriptLoader.instance.GAME_TICK_RATE)
        show = self.START_TIME - elapsed
        seconds = show.seconds
        minutes = seconds // 60
        seconds = seconds - minutes * 60
        ScriptLoader.instance.object_map["TimerText"].text = "{:02d}:{:02d}".format(minutes, seconds)

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                if shape.shape.obj.key == "controlsReset":
                    self._pressed = True
                words = shape.shape.obj.key.split("-")
                if len(words) == 3 and words[0] == "Tile" and words[2] == "UI":
                    tile_index = int(words[1])
                    self.spawnAt(tile_index)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                if (shape.shape.obj.key == "controlsReset") & self._pressed:
                    self.reset()
            self._pressed = False

    TOUCH_PENALTY = 5
    MAX_TOUCH_PENALTY = 20

    def touchBot(self):
        self._touches += 1
        penalty = min(self.TOUCH_PENALTY, self.MAX_TOUCH_PENALTY - self._touch_points)
        self._touch_points += penalty
        self.decrementScore(penalty)
        self.touchesChanged()

    def touchesChanged(self):
        ScriptLoader.instance.object_map["touchesCount"].text = str(self._touches)
        ScriptLoader.instance.object_map["touchesScore"].text = str(-self._touch_points)
