import datetime
import numpy as np
from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from simulation.world import World, stop_on_pause
from objects.base import objectFactory
from visual.manager import ScreenObjectManager

class SoccerInteractor(IInteractor):

    # Wait for 1 second after goal score.
    GOAL_SCORE_PAUSE_DELAY = 1
    START_TIME = datetime.timedelta(minutes=5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.names = kwargs.get('names', ['Team 1', 'Team 2'])
        self.spawns = kwargs.get('spawns')
        self.goals = kwargs.get('goals')
        self.show_goal_colliders = kwargs.get('show_goal_colliders', False)
        self.current_goal_score_tick = -1
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
        assert len(self.names) == len(self.spawns) and len(self.spawns) == len(self.goals), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.team_scores = []
        self.locateBots()
        if len(self.robots) % len(self.names) != 0:
            raise ValueError(f"Not an equal amount of robots per teams ({len(self.robots)} Robots, {len(self.names)} Teams)")
        self.BOTS_PER_TEAM = len(self.robots) // len(self.names)

        for x in range(len(self.names)):
            # Set up goal collider.
            pos = self.goals[x]['position']
            del self.goals[x]['position']
            obj = {
                'collider': 'inherit',
                'visual': self.goals[x],
                'position': pos,
                'physics': True
            }
            self.goal_colliders.append(objectFactory(**obj))
            if self.show_goal_colliders:
                ScreenObjectManager.instance.registerVisual(self.goal_colliders[-1].visual, f'Soccer_DEBUG_collider-{len(self.goal_colliders)}')
            # Set up team scores
            self.team_scores.append(0)
            # Set up team name
            ScriptLoader.instance.object_map[f'name{x+1}Text'].text = self.names[x]
        self.updateScoreText()
        self.resetPositions()
        for robot in self.robots:
            robot.robot_class.onSpawn()

    def updateScoreText(self):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f'score{x+1}Text'].text = str(self.team_scores[x])

    def resetPositions(self):
        # It is assumed that 2 robots to each team, with indexes increasing as we go across teams.
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                self.robots[team*self.BOTS_PER_TEAM + index].body.position = self.spawns[team][index][0]
                self.robots[team*self.BOTS_PER_TEAM + index].body.angle = self.spawns[team][index][1] * np.pi / 180
                self.robots[team*self.BOTS_PER_TEAM + index].body.velocity = np.array([0.0, 0.0])
                self.robots[team*self.BOTS_PER_TEAM + index].body.angular_velocity = 0
        ScriptLoader.instance.object_map['IR_BALL'].body.position = np.array([0, -18])
        ScriptLoader.instance.object_map['IR_BALL'].body.velocity = np.array([0., 0.])

    def tick(self, tick):
        super().tick(tick)
        if self.current_goal_score_tick != -1 and (tick - self.current_goal_score_tick) > self.GOAL_SCORE_PAUSE_DELAY * ScriptLoader.instance.GAME_TICK_RATE:
            self.current_goal_score_tick = -1
            World.instance.paused = False
        self.update_time()
        # TODO: Fix goal detection.
        """collider = objectFactory(**{
            'physics': True,
            'position': ScriptLoader.instance.object_map['IR_BALL'].position,
            'collider': {
                'name': 'Point'
            }
        }).collider
        for i, goal in enumerate(self.goal_colliders):
            if collider.getCollisionInfo(goal.collider)["collision"]:
                # GOAL!
                self.goalScoredIn(i, tick)
                break"""

    @stop_on_pause
    def update_time(self):
        self.time_tick += 1
        elapsed = datetime.timedelta(seconds=self.time_tick / ScriptLoader.instance.GAME_TICK_RATE)
        show = self.START_TIME - elapsed
        seconds = show.seconds
        minutes = seconds // 60
        seconds = seconds - minutes * 60
        ScriptLoader.instance.object_map['TimerText'].text = '{:02d}:{:02d}'.format(minutes, seconds)

    def goalScoredIn(self, teamIndex, tick):
        self.team_scores[1-teamIndex] += 1
        self.updateScoreText()
        self.resetPositions()
        # Pause the game temporarily
        World.instance.paused = True
        self.current_goal_score_tick = tick
