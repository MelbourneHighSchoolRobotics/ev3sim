import datetime
from ev3sim.visual.objects import visualFactory
from ev3sim.settings import ObjectSetting
import numpy as np
import pymunk
import pygame
from ev3sim.search_locations import batch_locations
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory, STATIC_CATEGORY
from ev3sim.objects.utils import local_space_to_world_space, magnitude_sq
from ev3sim.file_helper import find_abs
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.search_locations import preset_locations


class RescueInteractor(IInteractor):

    # Must occur before device interactors.
    SORT_ORDER = -10

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

    BOT_SPAWN_POSITION = [[[0, 0], 2]]
    TILE_DEFINITIONS = [
        {
            "path": "tiles/definitions/city_limits.yaml",
            "position": [-2, -2],
            "rotation": 0,
            "flip": False,
        },
    ]

    GAME_LENGTH_MINUTES = 5

    TILE_LENGTH = 30
    _pressed = False
    _touches = 0
    _touch_points = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_tick = 0
        self.hover_rect = visualFactory(
            name="Rectangle",
            width=30,
            height=30,
            position=(0, 0),
            fill=None,
            stroke="#ff0000",
            stroke_width=1,
            zPos=20,
        )
        self.hover_rect.key = "hover_rect"

    def spawnTiles(self):
        self.tiles = []
        for i, tile in enumerate(self.TILE_DEFINITIONS):
            self.tiles.append({})
            import yaml

            path = find_abs(tile["path"], allowed_areas=preset_locations)
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
                    if obj.get("name", "") == "Arc":
                        obj["rotation"] = 180 - obj.get("rotation", 0)
                        obj["angle"] = -obj["angle"]
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
            self.tiles[-1]["type"] = t.get("type", "follow")
            self.tiles[-1]["follows"] = []
            self.tiles[-1]["roam_status"] = []
            self.tiles[-1]["world_pos"] = base_pos
            self.tiles[-1]["rotation"] = base_rotation
            self.tiles[-1]["flip"] = flip
            if self.tiles[-1]["type"] == "follow":
                self.tiles[-1]["entries"] = t["entries"]
                self.tiles[-1]["exits"] = t["exits"]
                mname, cname = t.get("checker").rsplit(".", 1)
                import importlib

                klass = getattr(importlib.import_module(mname), cname)
                with open(find_abs(t["ui"], allowed_areas=preset_locations), "r") as f:
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
                                local_space_to_world_space(
                                    np.array(point), tile.get("rotation", 0) * np.pi / 180, base_pos
                                )
                            )
                            self.tiles[-1]["roam_status"].append(None)
                self.tiles[-1]["checker"] = klass(self.tiles[-1]["follows"], i, self, **t.get("checker_kwargs", {}))
            else:
                self.tiles[-1]["green_conns"] = t.get("green_conns", [])
            self.tiles[-1]["all_elems"] = ScriptLoader.instance.loadElements(t["elements"])
        connecting_objs = []
        for tile in self.tiles:
            # We need to add connections between green tiles if they exist.
            if tile["type"] == "follow":
                continue
            under = False
            right = False
            under_right = False
            for tile2 in self.tiles:
                if tile2["type"] == "follow":
                    continue
                if (
                    tile2["world_pos"][0] - tile["world_pos"][0] == self.TILE_LENGTH
                    and tile2["world_pos"][1] - tile["world_pos"][1] == 0
                ):
                    right = True
                if (
                    tile2["world_pos"][0] - tile["world_pos"][0] == 0
                    and tile2["world_pos"][1] - tile["world_pos"][1] == self.TILE_LENGTH
                ):
                    under = True
                if (
                    tile2["world_pos"][0] - tile["world_pos"][0] == self.TILE_LENGTH
                    and tile2["world_pos"][1] - tile["world_pos"][1] == self.TILE_LENGTH
                ):
                    under_right = True
            if under_right and under and right:
                # Draw a big square connecting all 4 tiles.
                key = "c1-" + str(tile["world_pos"][0]) + "-" + str(tile["world_pos"][1])
                connecting_objs.append(
                    {
                        "type": "visual",
                        "name": "Rectangle",
                        "width": 50,
                        "height": 50,
                        "fill": "grass_color",
                        "zPos": 0.3,
                        "key": key,
                        "position": [
                            tile["world_pos"][0] + self.TILE_LENGTH / 2,
                            tile["world_pos"][1] + self.TILE_LENGTH / 2,
                        ],
                        "sensorVisible": True,
                    }
                )
            else:
                if under:
                    key = "c2-" + str(tile["world_pos"][0]) + "-" + str(tile["world_pos"][1])
                    connecting_objs.append(
                        {
                            "type": "visual",
                            "name": "Rectangle",
                            "width": 20,
                            "height": 50,
                            "fill": "grass_color",
                            "zPos": 0.3,
                            "key": key,
                            "position": [tile["world_pos"][0], tile["world_pos"][1] + self.TILE_LENGTH / 2],
                            "sensorVisible": True,
                        }
                    )
                if right:
                    key = "c3-" + str(tile["world_pos"][0]) + "-" + str(tile["world_pos"][1])
                    connecting_objs.append(
                        {
                            "type": "visual",
                            "name": "Rectangle",
                            "width": 50,
                            "height": 20,
                            "fill": "grass_color",
                            "zPos": 0.3,
                            "key": key,
                            "position": [tile["world_pos"][0] + self.TILE_LENGTH / 2, tile["world_pos"][1]],
                            "sensorVisible": True,
                        }
                    )
        self.connecting_objs = ScriptLoader.instance.loadElements(connecting_objs)

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
        return self.TILE_UI_PADDING * 2 + self.TILE_UI_ELEM_HEIGHT * len(
            [tile for tile in self.tiles if tile["type"] == "follow"]
        )

    def spawnTileUI(self):
        elems = []
        i = 0
        for tile in self.tiles:
            if tile["type"] == "follow":
                elem = tile["ui_elem"]
                elem["key"] = f"Tile-{i}-UI"
                elem["position"] = [
                    -140,
                    -self.TILE_UI_ELEM_HEIGHT
                    * (i - (len([tile for tile in self.tiles if tile["type"] == "follow"]) - 1) / 2),
                ]
                elems.append(elem)
                i += 1
        for i, spawned in enumerate(ScriptLoader.instance.loadElements(elems)):
            self.tiles[i]["ui_spawned"] = spawned
            self.tiles[i]["checker"].onSpawn()
        ScriptLoader.instance.object_map["rescueBGMid"].scale = (1, self.tileUIHeight / self.TILE_UI_INITIAL_HEIGHT)
        ScriptLoader.instance.object_map["rescueBGMid"].calculatePoints()
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
            obj.shape.filter = pymunk.ShapeFilter(categories=self.FOLLOW_POINT_CATEGORY)
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
        self.START_TIME = datetime.timedelta(minutes=self.GAME_LENGTH_MINUTES)
        self.spawnTiles()
        self.spawnFollowPointPhysics()
        self.spawnTileUI()
        self.locateBots()
        assert len(self.robots) <= len(self.BOT_SPAWN_POSITION), "Not enough spawning locations specified."
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
        spawn_point = (
            self.tiles[tileIndex]["follows"][0][0][0]
            if isinstance(self.tiles[tileIndex]["follows"][0], (list, tuple))
            else self.tiles[tileIndex]["follows"][0]
        )
        for i in range(len(self.robots)):
            self.robots[i].body.angle = self.tiles[tileIndex]["rotation"]
            if self.tiles[tileIndex]["flip"]:
                self.robots[i].body.angle = self.robots[i].body.angle + np.pi
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
            if self.tiles[x]["type"] == "follow":
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
            robot.body.position = (
                np.array(
                    [
                        self.BOT_SPAWN_POSITION[i][0][0] * self.TILE_LENGTH,
                        self.BOT_SPAWN_POSITION[i][0][1] * self.TILE_LENGTH,
                    ]
                )
                + diff_radius * np.array([np.cos(diff_angle), np.sin(diff_angle)])
            )
            robot.body.angle = (
                (
                    self.BOT_SPAWN_POSITION[i][1]
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
            if self.tiles[i]["type"] == "follow":
                self.tiles[i]["checker"].tick(tick)
        # UI Tick
        if self._pressed:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "ui/controls_reset_pressed.png"
        else:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "ui/controls_reset_released.png"
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
        if event.type == pygame.MOUSEMOTION:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                words = shape.shape.obj.key.split("-")
                if len(words) == 3 and words[0] == "Tile" and words[2] == "UI":
                    tile_index = int(words[1])
                    # Highlight at tile.
                    if self.hover_rect.key not in ScreenObjectManager.instance.objects:
                        ScreenObjectManager.instance.registerVisual(self.hover_rect, self.hover_rect.key)
                    self.hover_rect.position = self.tiles[tile_index]["world_pos"]
                    break
            else:
                if self.hover_rect.key in ScreenObjectManager.instance.objects:
                    ScreenObjectManager.instance.unregisterVisual(self.hover_rect.key)

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


rescue_settings = {
    attr: ObjectSetting(RescueInteractor, attr)
    for attr in [
        "SHOW_FOLLOW_POINTS",
        "SHOW_ROBOT_COLLIDER",
        "ROBOT_CENTRE_RADIUS",
        "FOLLOW_POINT_RADIUS",
        "MAX_FOLLOW_DIST",
        "BOT_SPAWN_RADIUS",
        "BOT_SPAWN_ANGLE",
        "GAME_LENGTH_MINUTES",
        "BOT_SPAWN_POSITION",
        "TILE_DEFINITIONS",
    ]
}

from ev3sim.visual.settings.elements import NumberEntry, TextEntry, Checkbox, Button


def onClickMapEditor(filename):
    from ev3sim.visual.manager import ScreenObjectManager

    ScreenObjectManager.instance.pushScreen(
        ScreenObjectManager.SCREEN_RESCUE_EDIT,
        batch_file=find_abs(f"{filename}.yaml", batch_locations),
    )


visual_settings = [
    {"height": lambda s: 90, "objects": [TextEntry("__filename__", "BATCH NAME", None, (lambda s: (0, 20)))]},
    {
        "height": (lambda s: 240 if s[0] < 540 else 140),
        "objects": [
            NumberEntry(["settings", "rescue", "GAME_LENGTH_MINUTES"], 5, "Time allowed", (lambda s: (0, 20))),
            NumberEntry(
                ["settings", "rescue", "ROBOT_CENTRE_RADIUS"],
                3,
                "Collision Radius",
                (lambda s: (0, 70) if s[0] < 540 else (s[0] / 2, 20)),
            ),
            NumberEntry(
                ["settings", "rescue", "MAX_FOLLOW_DIST"],
                8,
                "Lack of Progress",
                (lambda s: (0, 120) if s[0] < 540 else (0, 70)),
            ),
            NumberEntry(
                ["settings", "rescue", "FOLLOW_POINT_RADIUS"],
                1,
                "Follow Radius",
                (lambda s: (0, 170) if s[0] < 540 else (s[0] / 2, 70)),
            ),
        ],
    },
    {
        "height": (lambda s: 120 if s[0] < 540 else 70),
        "objects": [
            Checkbox(["settings", "rescue", "SHOW_FOLLOW_POINTS"], False, "Show Follow Points", (lambda s: (0, 20))),
            Button("Map Editor", (lambda s: (0, 70) if s[0] < 540 else (s[0] / 2, 20)), onClickMapEditor),
        ],
    },
]
