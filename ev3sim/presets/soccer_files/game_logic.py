import datetime
import numpy as np
import math
import pymunk

from ev3sim.events import END_PENALTY, GOAL_SCORED, START_PENALTY
from ev3sim.objects.base import DYNAMIC_CATEGORY, objectFactory
from ev3sim.objects.utils import magnitude_sq
from ev3sim.presets.soccer_files.ui import SoccerUIInteractor
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.simulation.world import World, stop_on_pause


class SoccerLogicInteractor(IInteractor):

    # Must occur before device interactors.
    SORT_ORDER = -9
    instance = None

    ENFORCE_OUT_ON_WHITE = True
    BALL_RESET_ON_WHITE = True
    # Wait for 1 second after goal score.
    GOAL_SCORE_PAUSE_DELAY_SECONDS = 1
    GAME_HALF_LENGTH_MINUTES = 5
    # 5 Second penalty
    BOT_OUT_ON_WHITE_PENALTY_SECONDS = 30
    BALL_RESET_WHITE_DELAY_SECONDS = 5

    SPAWN_LOCATIONS = []
    PENALTY_LOCATIONS = []
    GOALS = []

    BALL_COLLISION_TYPE = 3
    GOAL_COLLISION_TYPE = 4
    FIELD_COLLISION_TYPE = 5
    BOT_COLLISION_TYPE = 6
    FIELD_BALL_COLLISION_TYPE = 7

    # Randomisation of spawn locations
    # Set these to 0 to disable spawn randomisation
    BOT_SPAWN_RADIUS = 3
    BALL_SPAWN_RADIUS = 1

    def __init__(self, **kwargs):
        SoccerLogicInteractor.instance = self
        super().__init__(**kwargs)
        # Various time trackers
        self.current_goal_score_tick = -1
        self.out_on_white_tick = 0
        self.time_tick = 0

    def generateGameColliders(self):
        self.ball_centre = objectFactory(
            **{
                "collider": "inherit",
                "visual": {"name": "Circle", "radius": 0.1},
                "physics": True,
                "key": "IR-BALL",
            }
        )
        self.field_ball = ScriptLoader.instance.object_map["centreFieldBallDetector"]
        self.field = ScriptLoader.instance.object_map["centreField"]
        for x in range(len(self.spawns)):
            # Set up goal collider.
            self.goals[x]["zPos"] = 6
            pos = self.goals[x]["position"]
            del self.goals[x]["position"]
            obj = {
                "collider": "inherit",
                "visual": self.goals[x],
                "position": pos,
                "physics": True,
                "static": True,
                "key": f"Goal-{x}",
            }
            self.goal_colliders.append(objectFactory(**obj))
        if SoccerUIInteractor.instance.SHOW_GOAL_COLLIDERS:
            from ev3sim.visual.manager import ScreenObjectManager

            for i, collider in enumerate(self.goal_colliders):
                ScreenObjectManager.instance.registerVisual(collider.visual, f"Soccer_DEBUG_collider-{i}")

    def setUpColliderEvents(self):
        saved_world_no = World.instance.spawn_no

        ### Set up collision types and sensors
        for i, bot in enumerate(self.robots):
            bot.shape.collision_type = self.BOT_COLLISION_TYPE
            bot.shape.bot_index = i

        self.ball_centre.shape.sensor = True
        self.ball_centre.shape.collision_type = self.BALL_COLLISION_TYPE
        World.instance.registerObject(self.ball_centre)

        self.field_ball.shape.sensor = True
        self.field_ball.shape.collision_type = self.FIELD_BALL_COLLISION_TYPE

        self.field.shape.sensor = True
        self.field.shape.collision_type = self.FIELD_COLLISION_TYPE

        for x in range(len(self.spawns)):
            self.goal_colliders[x].shape.sensor = True
            self.goal_colliders[x].shape.collision_type = self.GOAL_COLLISION_TYPE
            self.goal_colliders[x].shape.goal_index = x
            World.instance.registerObject(self.goal_colliders[x])

        ### Set up collision handlers
        # Goal scoring event
        handler = World.instance.space.add_collision_handler(self.BALL_COLLISION_TYPE, self.GOAL_COLLISION_TYPE)

        def handle_collide(arbiter, space, data):
            if World.instance.spawn_no != saved_world_no:
                return
            a, b = arbiter.shapes
            if hasattr(a, "goal_index"):
                self.goalScoredIn(a.goal_index)
            elif hasattr(b, "goal_index"):
                self.goalScoredIn(b.goal_index)
            else:
                raise ValueError("Two objects with collision types used by soccer don't have a goal index.")
            return False

        handler.begin = handle_collide

        # Ball leaves field event
        if self.BALL_RESET_ON_WHITE:
            handler = World.instance.space.add_collision_handler(
                self.FIELD_BALL_COLLISION_TYPE, self.BALL_COLLISION_TYPE
            )

            def handle_separate_ball(arbiter, space, data):
                if World.instance.spawn_no != saved_world_no:
                    return
                self.out_on_white_tick = self.BALL_RESET_WHITE_DELAY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
                return False

            def handle_collide_ball(arbiter, space, data):
                if World.instance.spawn_no != saved_world_no:
                    return
                self.out_on_white_tick = 0
                return False

            handler.separate = handle_separate_ball
            handler.begin = handle_collide_ball

        # Bot leaves field event
        if self.ENFORCE_OUT_ON_WHITE:
            handler = World.instance.space.add_collision_handler(self.FIELD_COLLISION_TYPE, self.BOT_COLLISION_TYPE)

            def handle_separate(arbiter, space, data):
                if World.instance.spawn_no != saved_world_no:
                    return
                a, b = arbiter.shapes
                if hasattr(a, "bot_index"):
                    self.penaliseBot(a.bot_index)
                elif hasattr(b, "bot_index"):
                    self.penaliseBot(b.bot_index)
                else:
                    raise ValueError("Two objects with collision types used by soccer don't have a bot index.")
                return False

            handler.separate = handle_separate

    def startUp(self):
        super().startUp()
        self.START_TIME = datetime.timedelta(minutes=self.GAME_HALF_LENGTH_MINUTES, seconds=0.5)
        self.spawns = self.SPAWN_LOCATIONS[:]
        self.penalty = self.PENALTY_LOCATIONS[:]
        self.goals = self.GOALS[:]
        assert len(self.spawns) == len(self.goals), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.bot_penalties = [0] * len(self.robots)
        self.BOTS_PER_TEAM = math.ceil(len(self.robots) / len(self.spawns))

        self.generateGameColliders()
        self.setUpColliderEvents()

        for robot in self.robots:
            robot.robot_class.onSpawn()
        self.reset()

    def reset(self):
        self.team_scores = [0 for _ in self.spawns]
        SoccerUIInteractor.instance.updateScoreText(self.team_scores)
        self.resetPositions()
        self.time_tick = 0
        self.restartBots()

    def resetPositions(self):
        for team in range(len(self.spawns)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team + index * len(self.spawns)
                if actual_index >= len(self.robots):
                    break
                # Generate a uniformly random point in radius of spawn for bot.
                diff_radius = Randomiser.random() * self.BOT_SPAWN_RADIUS
                diff_angle = Randomiser.random() * 2 * np.pi
                self.robots[actual_index].body.position = [
                    self.spawns[team][index][0][0] + diff_radius * np.cos(diff_angle),
                    self.spawns[team][index][0][1] + diff_radius * np.sin(diff_angle),
                ]
                self.robots[actual_index].body.angle = self.spawns[team][index][1] * np.pi / 180
                self.robots[actual_index].body.velocity = (0.0, 0.0)
                self.robots[actual_index].body.angular_velocity = 0
        # Generate position for ball.
        diff_radius = Randomiser.random() * self.BALL_SPAWN_RADIUS
        diff_angle = Randomiser.random() * 2 * np.pi
        ScriptLoader.instance.object_map["IR_BALL"].body.position = [
            diff_radius * np.cos(diff_angle),
            diff_radius * np.sin(diff_angle) - 18,
        ]
        ScriptLoader.instance.object_map["IR_BALL"].body.velocity = (0.0, 0.0)
        for idx in range(len(self.bot_penalties)):
            if self.bot_penalties[idx] > 0:
                self.finishPenalty(idx)

    def resetBallClosest(self):
        all_keys = ("midSpot", "topSpot", "botSpot")
        available_keys = [
            key
            for key in all_keys
            if not World.instance.space.point_query(
                [float(v) for v in ScriptLoader.instance.object_map[key].position],
                0.0,
                pymunk.ShapeFilter(mask=DYNAMIC_CATEGORY),
            )
        ]
        best_key = sorted(
            [
                (
                    magnitude_sq(
                        [
                            a - b
                            for a, b in zip(
                                ScriptLoader.instance.object_map["IR_BALL"].body.position,
                                ScriptLoader.instance.object_map[key].position,
                            )
                        ]
                    ),
                    key,
                )
                for key in (available_keys if available_keys else all_keys)
            ]
        )[0][1]
        ScriptLoader.instance.object_map["IR_BALL"].body.position = [
            float(v) for v in ScriptLoader.instance.object_map[best_key].position
        ]
        ScriptLoader.instance.object_map["IR_BALL"].body.velocity = (0.0, 0.0)

    def goalScoredIn(self, teamIndex):
        self.team_scores[1 - teamIndex] += 1
        SoccerUIInteractor.instance.updateScoreText(self.team_scores)
        self.resetPositions()
        # Pause the game temporarily
        World.instance.paused = True
        self.current_goal_score_tick = self.cur_tick
        for team in range(len(self.spawns)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team + index * len(self.spawns)
                if actual_index >= len(self.robots):
                    break
                ScriptLoader.instance.sendEvent(
                    f"Robot-{actual_index}", GOAL_SCORED, {"against_you": team == teamIndex}
                )

    def penaliseBot(self, botIndex):
        self.bot_penalties[botIndex] = self.BOT_OUT_ON_WHITE_PENALTY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
        self.robots[botIndex].clickable = False
        ScriptLoader.instance.sendEvent(f"Robot-{botIndex}", START_PENALTY, {})
        to_go = datetime.timedelta(seconds=self.bot_penalties[botIndex] / ScriptLoader.instance.GAME_TICK_RATE)
        SoccerUIInteractor.instance.startPenalty(botIndex, str(to_go.seconds))

    def finishPenalty(self, botIndex):
        self.bot_penalties[botIndex] = 0
        self.robots[botIndex].clickable = True
        self.robots[botIndex].body.position = self.spawns[botIndex % len(self.spawns)][botIndex // len(self.spawns)][0]
        self.robots[botIndex].body.angle = (
            self.spawns[botIndex % len(self.spawns)][botIndex // len(self.spawns)][1] * np.pi / 180
        )
        self.robots[botIndex].body.velocity = (0.0, 0.0)
        self.robots[botIndex].body.angular_velocity = 0
        ScriptLoader.instance.sendEvent(f"Robot-{botIndex}", END_PENALTY, {})
        SoccerUIInteractor.instance.endPenalty(botIndex)

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
        self.ball_centre.body.position = ScriptLoader.instance.object_map["IR_BALL"].body.position
        if (
            self.current_goal_score_tick != -1
            and (tick - self.current_goal_score_tick)
            > self.GOAL_SCORE_PAUSE_DELAY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
        ):
            # After some delay start the next point.
            self.current_goal_score_tick = -1
            World.instance.paused = False

        self.update_time()

    def afterPhysics(self):
        for team in range(len(self.spawns)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team + index * len(self.spawns)
                if actual_index >= len(self.robots):
                    break
                if self.bot_penalties[actual_index] > 0:
                    self.robots[actual_index].body.position = self.penalty[team][index][0]
                    self.robots[actual_index].body.angle = self.penalty[team][index][1] * np.pi / 180
                    self.robots[actual_index].position = np.array(self.robots[actual_index].body.position)
                    self.robots[actual_index].rotation = self.robots[actual_index].body.angle

    @stop_on_pause
    def update_time(self):
        self.time_tick += 1
        elapsed = datetime.timedelta(seconds=self.time_tick / ScriptLoader.instance.GAME_TICK_RATE)
        show = self.START_TIME - elapsed
        seconds = show.seconds
        minutes = seconds // 60
        seconds = seconds - minutes * 60
        if self.GAME_HALF_LENGTH_MINUTES * 60 - self.time_tick / ScriptLoader.instance.GAME_TICK_RATE < 0:
            World.instance.paused = True
            return
        ScriptLoader.instance.object_map["TimerText"].text = "{:02d}:{:02d}".format(minutes, seconds)

        for idx in range(len(self.bot_penalties)):
            if self.bot_penalties[idx] > 0:
                self.bot_penalties[idx] -= 1
                to_go = datetime.timedelta(seconds=self.bot_penalties[idx] / ScriptLoader.instance.GAME_TICK_RATE)
                SoccerUIInteractor.instance.setPenaltyText(idx, str(to_go.seconds))
                if self.bot_penalties[idx] == 0:
                    self.finishPenalty(idx)

        if self.out_on_white_tick > 0:
            self.out_on_white_tick -= 1
            if self.out_on_white_tick == 0:
                self.resetBallClosest()
