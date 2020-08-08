import datetime
import numpy as np
import math
from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from simulation.world import World, stop_on_pause
from objects.base import objectFactory
from objects.utils import local_space_to_world_space

class RescueInteractor(IInteractor):

    START_TIME = datetime.timedelta(minutes=5)

    TILE_LENGTH = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawns = kwargs.get('spawns')
        self.time_tick = 0
        for i, tile in enumerate(kwargs['tiles']):
            import yaml
            with open(tile['path'], 'r') as f:
                t = yaml.safe_load(f)
            for obj in t:
                rel_pos = np.array(obj.get('position', [0, 0]))
                base_pos = np.array(tile.get('position', [0, 0]))
                # Transfer to rescue space.
                base_pos = [base_pos[0] * self.TILE_LENGTH, base_pos[1] * self.TILE_LENGTH]
                obj['rotation'] = (obj.get('rotation', 0) + tile.get('rotation', 0)) * np.pi / 180
                obj['position'] = local_space_to_world_space(rel_pos, tile.get('rotation', 0) * np.pi / 180, base_pos)
                obj['sensorVisible'] = True
                k = obj['key']
                obj['key'] = f'Tile-{i}-{k}'
            ScriptLoader.instance.loadElements(t)
            

    def locateBots(self):
        self.robots = []
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
            bot_index += 1

        if len(self.robots) == 0:
            raise ValueError("No robots loaded.")

    def startUp(self):
        self.locateBots()
        assert len(self.robots) <= len(self.spawns), "Not enough spawning locations specified."
        self.scores = [0]*len(self.robots)

        self.resetPositions()

        for robot in self.robots:
            robot.robot_class.onSpawn()

    def resetPositions(self):
        for i, robot in enumerate(self.robots):
            robot.body.position = [self.spawns[i][0][0] * self.TILE_LENGTH, self.spawns[i][0][1] * self.TILE_LENGTH]
            robot.body.angle = self.spawns[i][1] * np.pi / 180
            robot.body.velocity = np.array([0.0, 0.0])
            robot.body.angular_velocity = 0

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
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
