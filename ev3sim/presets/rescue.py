import datetime
import numpy as np
import math
import pymunk
import pygame
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory, STATIC_CATEGORY
from ev3sim.objects.utils import local_space_to_world_space, magnitude_sq
from ev3sim.file_helper import find_abs
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace

class RescueInteractor(IInteractor):

    FOLLOW_POINT_CATEGORY = 0b1000
    SHOW_FOLLOW_POINTS = True
    SHOW_ROBOT_COLLIDER = True
    FOLLOW_POINT_COLLISION_TYPE = 5
    ROBOT_CENTRE_COLLISION_TYPE = 6
    ROBOT_CENTRE_RADIUS = 3
    FOLLOW_POINT_RADIUS = 1
    # You can be at most this far from the previous follow point before lack of progress is called.
    MAX_FOLLOW_DIST = 8

    START_TIME = datetime.timedelta(minutes=5)

    TILE_LENGTH = 30
    _pressed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawns = kwargs.get('spawns')
        self.time_tick = 0
        self.tiles = []
        for i, tile in enumerate(kwargs['tiles']):
            self.tiles.append({})
            import yaml
            path = find_abs(tile['path'], allowed_areas=['local/presets/', 'local', 'package/presets/', 'package'])
            with open(path, 'r') as f:
                t = yaml.safe_load(f)
            self.maxZpos = 0
            base_pos = np.array(tile.get('position', [0, 0]))
            # Transfer to rescue space.
            base_pos = [base_pos[0] * self.TILE_LENGTH, base_pos[1] * self.TILE_LENGTH]
            for obj in t['elements']:
                rel_pos = np.array(obj.get('position', [0, 0]))
                obj['rotation'] = (obj.get('rotation', 0) + tile.get('rotation', 0)) * np.pi / 180
                obj['position'] = local_space_to_world_space(rel_pos, tile.get('rotation', 0) * np.pi / 180, base_pos)
                obj['sensorVisible'] = True
                k = obj['key']
                obj['key'] = f'Tile-{i}-{k}'
                self.maxZpos = max(self.maxZpos, obj.get('zPos', 0))
            t['elements'].append({
                'position': local_space_to_world_space(np.array([0, 0]), tile.get('rotation', 0) * np.pi / 180, base_pos),
                'rotation': tile.get('rotation', 0) * np.pi / 180,
                'type': 'visual',
                'name': 'Rectangle',
                'width': self.TILE_LENGTH,
                'height': self.TILE_LENGTH,
                'fill': None,
                'stroke_width': 0.1,
                'stroke': 'rescue_outline_color',
                'zPos': self.maxZpos + 0.1,
                'key': f'Tile-{i}-outline',
                'sensorVisible': False,
            })
            self.tiles[-1]['follows'] = []
            mname, cname = t.get('checker').rsplit('.', 1)
            import importlib
            klass = getattr(importlib.import_module(mname), cname)
            with open(find_abs(t['ui'], allowed_areas=['local/presets/', 'local', 'package/presets/', 'package']), 'r') as f:
                self.tiles[-1]['ui_elem'] = yaml.safe_load(f)
            for j, (x, y) in enumerate(t['follow_points']):
                self.tiles[-1]['follows'].append(local_space_to_world_space(np.array([x, y]), tile.get('rotation', 0) * np.pi / 180, base_pos))
            self.tiles[-1]['checker'] = klass(self.tiles[-1]['follows'], i, self)
            ScriptLoader.instance.loadElements(t['elements'])

    def collidedFollowPoint(self, follow_indexes):
        if self.follow_completed[follow_indexes[0]][follow_indexes[1]]:
            return
        self.current_follow = follow_indexes
        self.follow_completed[follow_indexes[0]][follow_indexes[1]] = True
        self.tiles[follow_indexes[0]]['follow_colliders'][follow_indexes[1]].visual.fill = '#00ff00'
        self.tiles[follow_indexes[0]]['checker'].onNewFollowPoint(self.follow_completed[follow_indexes[0]])

    def spawnFollowPointPhysics(self):
        for i, tile in enumerate(self.tiles):
            tile['follow_colliders'] = []
            for j, pos in enumerate(tile['follows']):
                obj = objectFactory(**{
                    'collider': 'inherit',
                    'visual': {
                        'name': 'Circle',
                        'radius': self.FOLLOW_POINT_RADIUS,
                        'position': pos,
                        'fill': '#ff0000' if self.SHOW_FOLLOW_POINTS else None,
                        'stroke_width': 0,
                        'sensorVisible': False,
                        'zPos': self.maxZpos + 0.2,
                    },
                    'position': pos,
                    'physics': True,
                    'static': True,
                    'key': f'Tile-{i}-follow-{j}',
                })
                obj.shape.filter = pymunk.ShapeFilter(categories=self.FOLLOW_POINT_CATEGORY)
                obj.shape.sensor = True
                obj.shape._follow_indexes = (i, j)
                obj.shape.collision_type = self.FOLLOW_POINT_COLLISION_TYPE
                World.instance.registerObject(obj)
                if self.SHOW_FOLLOW_POINTS:
                    ScreenObjectManager.instance.registerObject(obj, obj.key)
                tile['follow_colliders'].append(obj)

    TILE_UI_ELEM_HEIGHT = 10
    TILE_UI_PADDING = 20

    @property
    def tileUIHeight(self):
        return self.TILE_UI_PADDING * 2 + self.TILE_UI_ELEM_HEIGHT * len(self.tiles)

    def spawnTileUI(self):
        elems = []
        for i, tile in enumerate(self.tiles):
            elem = tile['ui_elem']
            elem['key'] = f'Tile-{i}-UI'
            elem['position'] = [-140, -self.TILE_UI_ELEM_HEIGHT * (i - (len(self.tiles)-1) / 2)]
            elems.append(elem)
        for i, spawned in enumerate(ScriptLoader.instance.loadElements(elems)):
            self.tiles[i]['ui_spawned'] = spawned

    def locateBots(self):
        self.robots = []
        self.bot_follows = []
        bot_index = 0
        while True:
            # Find the next robot.
            possible_keys = []
            for key in ScriptLoader.instance.object_map.keys():
                if key.startswith(f'Robot-{bot_index}'):
                    possible_keys.append(key)
            if len(possible_keys) == 0:
                break
            possible_keys.sort(key=len)
            self.robots.append(ScriptLoader.instance.object_map[possible_keys[0]])
            # Spawn the robot follow point collider.
            obj = objectFactory(**{
                'collider': 'inherit',
                'visual': {
                    'name': 'Circle',
                    'radius': self.ROBOT_CENTRE_RADIUS,
                    'fill': '#00ff00' if self.SHOW_ROBOT_COLLIDER else None,
                    'stroke_width': 0,
                    'sensorVisible': False,
                    'zPos': 100,
                },
                'physics': True,
                'key': f'Robot-{bot_index}-follow',
            })
            obj.shape.sensor = True
            obj.shape.collision_type = self.ROBOT_CENTRE_COLLISION_TYPE
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
        self.scores = [0]*len(self.robots)

        self.reset()
        for i in range(len(self.robots)):
            self.bot_follows[i].body.position = self.robots[i].body.position
        self.addCollisionHandler()

        for robot in self.robots:
            robot.robot_class.onSpawn()

    def addCollisionHandler(self):
        handler = World.instance.space.add_collision_handler(self.FOLLOW_POINT_COLLISION_TYPE, self.ROBOT_CENTRE_COLLISION_TYPE)
        def handle_collide(arbiter, space, data):
            a, b = arbiter.shapes
            if hasattr(a, '_follow_indexes'):
                self.collidedFollowPoint(a._follow_indexes)
            elif hasattr(b, '_follow_indexes'):
                self.collidedFollowPoint(b._follow_indexes)
            else:
                raise ValueError("Two objects with collision types used by rescue don't have a tile follow point.")
            return False
        handler.begin = handle_collide

    def spawnAt(self, tileIndex):
        self.current_follow = None
        spawn_point = self.tiles[tileIndex]['follows'][0]
        for i in range(len(self.robots)):
            self.robots[i].body.position += spawn_point - self.bot_follows[i].body.position

    def reset(self):
        self.resetPositions()
        self.current_follow = None
        self.follow_completed = [
            [
                False for x in y['follows']
            ]
            for y in self.tiles
        ]
        self.time_tick = 0

    def resetPositions(self):
        for i, robot in enumerate(self.robots):
            robot.body.position = [self.spawns[i][0][0] * self.TILE_LENGTH, self.spawns[i][0][1] * self.TILE_LENGTH]
            robot.body.angle = self.spawns[i][1] * np.pi / 180
            robot.body.velocity = np.array([0.0, 0.0])
            robot.body.angular_velocity = 0

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
        for i in range(len(self.robots)):
            self.bot_follows[i].body.position = self.robots[i].body.position
            # Ensure visual is not 1 frame behind.
            self.bot_follows[i].position = self.robots[i].body.position
        if self.current_follow is not None and not World.instance.paused:
            distance = magnitude_sq(self.bot_follows[i].position - self.tiles[self.current_follow[0]]['follows'][self.current_follow[1]])
            if distance > self.MAX_FOLLOW_DIST * self.MAX_FOLLOW_DIST:
                print("Lack of Progress!")
                World.instance.paused = True
                self.current_follow = None
        # UI Tick
        if self._pressed:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = 'assets/ui/controls_reset_pressed.png'
        else:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = 'assets/ui/controls_reset_released.png'
        self.update_time()

    @stop_on_pause
    def update_time(self):
        self.time_tick += 1
        elapsed = datetime.timedelta(seconds=self.time_tick / ScriptLoader.instance.GAME_TICK_RATE)
        show = self.START_TIME - elapsed
        seconds = show.seconds
        minutes = seconds // 60
        seconds = seconds - minutes * 60
        ScriptLoader.instance.object_map['TimerText'].text = '{:02d}:{:02d}'.format(minutes, seconds)

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                if shape.shape.obj.key == "controlsReset":
                    self._pressed = True
                words = shape.shape.obj.key.split('-')
                if len(words) == 3 and words[0] == 'Tile' and words[2] == 'UI':
                    tile_index = int(words[1])
                    self.spawnAt(tile_index)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                if (shape.shape.obj.key == "controlsReset") & self._pressed:
                    self.reset()
                self._pressed = False
            if len(shapes) == 0: self._pressed = False