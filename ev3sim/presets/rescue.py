import datetime
import numpy as np
import math
from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from simulation.world import World, stop_on_pause
from objects.base import objectFactory
from visual.manager import ScreenObjectManager

class RescueInteractor(IInteractor):

    START_TIME = datetime.timedelta(minutes=5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawns = kwargs.get('spawns')
        self.time_tick = 0
    
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
            robot.body.position = self.spawns[i][0]
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
