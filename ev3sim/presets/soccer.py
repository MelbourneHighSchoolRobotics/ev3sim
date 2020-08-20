import datetime
import numpy as np
import math
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory
from ev3sim.visual.manager import ScreenObjectManager

class SoccerInteractor(IInteractor):

    # Wait for 1 second after goal score.
    GOAL_SCORE_PAUSE_DELAY = 1
    START_TIME = datetime.timedelta(minutes=5)

    BALL_COLLISION_TYPE = 3
    GOAL_COLLISION_TYPE = 4

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
        self.BOTS_PER_TEAM = math.ceil(len(self.robots) / len(self.names))

        self.ball_centre = objectFactory(**{
            'collider': 'inherit',
            'visual': {
                'name': 'Circle',
                'radius': 0.1
            },
            'physics': True,
            'key': 'IR-BALL',
        })
        self.ball_centre.shape.sensor = True
        self.ball_centre.shape.collision_type = self.BALL_COLLISION_TYPE
        World.instance.registerObject(self.ball_centre)

        handler = World.instance.space.add_collision_handler(self.BALL_COLLISION_TYPE, self.GOAL_COLLISION_TYPE)
        def handle_collide(arbiter, space, data):
            a, b = arbiter.shapes
            if hasattr(a, 'goal_index'):
                self.goalScoredIn(a.goal_index)
            elif hasattr(b, 'goal_index'):
                self.goalScoredIn(b.goal_index)
            else:
                raise ValueError("Two objects with collision types used by soccer don't have a goal index.")
            return False
        handler.begin = handle_collide

        for x in range(len(self.names)):
            # Set up goal collider.
            pos = self.goals[x]['position']
            del self.goals[x]['position']
            obj = {
                'collider': 'inherit',
                'visual': self.goals[x],
                'position': pos,
                'physics': True,
                'static': True,
                'key':  f'Goal-{x}',
            }
            self.goal_colliders.append(objectFactory(**obj))
            self.goal_colliders[-1].shape.sensor = True
            self.goal_colliders[-1].shape.collision_type = self.GOAL_COLLISION_TYPE
            self.goal_colliders[-1].shape.goal_index = x
            World.instance.registerObject(self.goal_colliders[-1])
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
                actual_index = team*self.BOTS_PER_TEAM + index
                if actual_index >= len(self.robots):
                    break
                self.robots[actual_index].body.position = self.spawns[team][index][0]
                self.robots[actual_index].body.angle = self.spawns[team][index][1] * np.pi / 180
                self.robots[actual_index].body.velocity = np.array([0.0, 0.0])
                self.robots[actual_index].body.angular_velocity = 0
        ScriptLoader.instance.object_map['IR_BALL'].body.position = np.array([0, -18])
        ScriptLoader.instance.object_map['IR_BALL'].body.velocity = np.array([0., 0.])

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
        self.ball_centre.body.position = ScriptLoader.instance.object_map['IR_BALL'].body.position
        if self.current_goal_score_tick != -1 and (tick - self.current_goal_score_tick) > self.GOAL_SCORE_PAUSE_DELAY * ScriptLoader.instance.GAME_TICK_RATE:
            self.current_goal_score_tick = -1
            World.instance.paused = False
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

    def goalScoredIn(self, teamIndex):
        self.team_scores[1-teamIndex] += 1
        self.updateScoreText()
        self.resetPositions()
        # Pause the game temporarily
        World.instance.paused = True
        self.current_goal_score_tick = self.cur_tick
