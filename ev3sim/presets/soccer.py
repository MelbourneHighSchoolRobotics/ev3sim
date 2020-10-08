import datetime
import pygame
import numpy as np
import math
import pymunk
from ev3sim.events import GAME_RESET, GOAL_SCORED, START_PENALTY, END_PENALTY
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory
from ev3sim.objects.utils import magnitude_sq
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.objects.base import DYNAMIC_CATEGORY, STATIC_CATEGORY


class SoccerInteractor(IInteractor):

    # Must occur before device interactors.
    SORT_ORDER = -10

    SHOW_GOAL_COLLIDERS = True
    ENFORCE_OUT_ON_WHITE = True
    BALL_RESET_ON_WHITE = True
    # Wait for 1 second after goal score.
    GOAL_SCORE_PAUSE_DELAY_SECONDS = 1
    GAME_HALF_LENGTH_MINUTES = 5
    # 5 Second penalty
    BOT_OUT_ON_WHITE_PENALTY_SECONDS = 30
    BALL_RESET_WHITE_DELAY_SECONDS = 5

    TEAM_NAMES = []
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

    _pressed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.START_TIME = datetime.timedelta(minutes=self.GAME_HALF_LENGTH_MINUTES)
        self.names = self.TEAM_NAMES[:]
        self.spawns = self.SPAWN_LOCATIONS[:]
        self.penalty = self.PENALTY_LOCATIONS[:]
        self.goals = self.GOALS[:]
        self.current_goal_score_tick = -1
        self.out_on_white_tick = 0
        self.time_tick = 0
        self.update_time_text = True

    def locateBots(self):
        self.robots = []
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
            self.robots[-1].shape.collision_type = self.BOT_COLLISION_TYPE
            self.robots[-1].shape.bot_index = bot_index
            bot_index += 1
        self.bot_penalties = [0] * bot_index

        if len(self.robots) == 0:
            raise ValueError("No robots loaded.")

    def startUp(self):
        assert len(self.names) == len(self.spawns) and len(self.spawns) == len(
            self.goals
        ), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.team_scores = []
        self.locateBots()
        self.BOTS_PER_TEAM = math.ceil(len(self.robots) / len(self.names))

        self.ball_centre = objectFactory(
            **{
                "collider": "inherit",
                "visual": {"name": "Circle", "radius": 0.1},
                "physics": True,
                "key": "IR-BALL",
            }
        )
        self.ball_centre.shape.sensor = True
        self.ball_centre.shape.collision_type = self.BALL_COLLISION_TYPE
        World.instance.registerObject(self.ball_centre)

        handler = World.instance.space.add_collision_handler(self.BALL_COLLISION_TYPE, self.GOAL_COLLISION_TYPE)

        def handle_collide(arbiter, space, data):
            a, b = arbiter.shapes
            if hasattr(a, "goal_index"):
                self.goalScoredIn(a.goal_index)
            elif hasattr(b, "goal_index"):
                self.goalScoredIn(b.goal_index)
            else:
                raise ValueError("Two objects with collision types used by soccer don't have a goal index.")
            return False

        handler.begin = handle_collide

        # Initialise field collider for ball reset on white
        self.field_ball = ScriptLoader.instance.object_map["centreFieldBallDetector"]
        self.field_ball.shape.sensor = True
        self.field_ball.shape.collision_type = self.FIELD_BALL_COLLISION_TYPE
        if self.BALL_RESET_ON_WHITE:
            handler = World.instance.space.add_collision_handler(
                self.FIELD_BALL_COLLISION_TYPE, self.BALL_COLLISION_TYPE
            )

            def handle_separate_ball(arbiter, space, data):
                self.out_on_white_tick = self.BALL_RESET_WHITE_DELAY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
                return False

            def handle_collide_ball(arbiter, space, data):
                self.out_on_white_tick = 0
                return False

            handler.separate = handle_separate_ball
            handler.begin = handle_collide_ball

        # Initialise field collider for out on white
        self.field = ScriptLoader.instance.object_map["centreField"]
        self.field.shape.sensor = True
        self.field.shape.collision_type = self.FIELD_COLLISION_TYPE
        if self.ENFORCE_OUT_ON_WHITE:
            handler = World.instance.space.add_collision_handler(self.FIELD_COLLISION_TYPE, self.BOT_COLLISION_TYPE)

            def handle_separate(arbiter, space, data):
                a, b = arbiter.shapes
                if hasattr(a, "bot_index"):
                    self.penaliseBot(a.bot_index)
                elif hasattr(b, "bot_index"):
                    self.penaliseBot(b.bot_index)
                else:
                    raise ValueError("Two objects with collision types used by soccer don't have a bot index.")
                return False

            handler.separate = handle_separate

        for x in range(len(self.names)):
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
            self.goal_colliders[-1].shape.sensor = True
            self.goal_colliders[-1].shape.collision_type = self.GOAL_COLLISION_TYPE
            self.goal_colliders[-1].shape.goal_index = x
            World.instance.registerObject(self.goal_colliders[-1])
            if self.SHOW_GOAL_COLLIDERS:
                ScreenObjectManager.instance.registerVisual(
                    self.goal_colliders[-1].visual, f"Soccer_DEBUG_collider-{len(self.goal_colliders)}"
                )
            # Set up team scores
            self.team_scores.append(0)
            # Set up team name
            ScriptLoader.instance.object_map[f"name{x+1}Text"].text = self.names[x]
        self.updateScoreText()
        self.resetPositions()
        for robot in self.robots:
            robot.robot_class.onSpawn()

    def updateScoreText(self):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f"score{x+1}Text"].text = str(self.team_scores[x])

    def reset(self):
        self.team_scores = [0 for x in self.names]
        self.updateScoreText()
        self.resetPositions()
        self.time_tick = 0
        self.update_time_text = True
        for robotID in ScriptLoader.instance.robots.keys():
            ScriptLoader.instance.sendEvent(robotID, GAME_RESET, {})

    def resetPositions(self):
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team * self.BOTS_PER_TEAM + index
                if actual_index >= len(self.robots):
                    break
                # Generate a uniformly random point in radius of spawn for bot.
                diff_radius = Randomiser.random() * self.BOT_SPAWN_RADIUS
                diff_angle = Randomiser.random() * 2 * np.pi
                self.robots[actual_index].body.position = self.spawns[team][index][0] + diff_radius * np.array(
                    [np.cos(diff_angle), np.sin(diff_angle)]
                )
                self.robots[actual_index].body.angle = self.spawns[team][index][1] * np.pi / 180
                self.robots[actual_index].body.velocity = np.array([0.0, 0.0])
                self.robots[actual_index].body.angular_velocity = 0
        # Generate position for ball.
        diff_radius = Randomiser.random() * self.BALL_SPAWN_RADIUS
        diff_angle = Randomiser.random() * 2 * np.pi
        ScriptLoader.instance.object_map["IR_BALL"].body.position = np.array([0, -18]) + diff_radius * np.array(
            [np.cos(diff_angle), np.sin(diff_angle)]
        )
        ScriptLoader.instance.object_map["IR_BALL"].body.velocity = np.array([0.0, 0.0])
        for idx in range(len(self.bot_penalties)):
            if self.bot_penalties[idx] > 0:
                self.finishPenalty(idx)

    def resetBallClosest(self):
        all_keys = ("midSpot", "topSpot", "botSpot")
        available_keys = [
            key
            for key in all_keys
            if not World.instance.space.point_query(
                ScriptLoader.instance.object_map[key].position, 0.0, pymunk.ShapeFilter(mask=DYNAMIC_CATEGORY)
            )
        ]
        best_key = sorted(
            [
                (
                    magnitude_sq(
                        ScriptLoader.instance.object_map["IR_BALL"].body.position
                        - ScriptLoader.instance.object_map[key].position
                    ),
                    key,
                )
                for key in (available_keys if available_keys else all_keys)
            ]
        )[0][1]
        ScriptLoader.instance.object_map["IR_BALL"].body.position = ScriptLoader.instance.object_map[best_key].position
        ScriptLoader.instance.object_map["IR_BALL"].body.velocity = np.array([0.0, 0.0])

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
        self.ball_centre.body.position = ScriptLoader.instance.object_map["IR_BALL"].body.position
        if (
            self.current_goal_score_tick != -1
            and (tick - self.current_goal_score_tick)
            > self.GOAL_SCORE_PAUSE_DELAY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
        ):
            self.current_goal_score_tick = -1
            World.instance.paused = False

        # UI Tick
        if self._pressed:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "assets/ui/controls_reset_pressed.png"
        else:
            ScriptLoader.instance.object_map[
                "controlsReset"
            ].visual.image_path = "assets/ui/controls_reset_released.png"
        self.update_time()

    def afterPhysics(self):
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team * self.BOTS_PER_TEAM + index
                if actual_index >= len(self.robots):
                    break
                if self.bot_penalties[actual_index] > 0:
                    self.robots[actual_index].body.position = self.penalty[team][index][0]
                    self.robots[actual_index].body.angle = self.penalty[team][index][1] * np.pi / 180
                    self.robots[actual_index].position = self.robots[actual_index].body.position
                    self.robots[actual_index].rotation = self.robots[actual_index].body.angle

    @stop_on_pause
    def update_time(self):
        self.time_tick += 1
        if not self.update_time_text:
            return
        elapsed = datetime.timedelta(seconds=self.time_tick / ScriptLoader.instance.GAME_TICK_RATE)
        show = self.START_TIME - elapsed
        seconds = show.seconds
        minutes = seconds // 60
        seconds = seconds - minutes * 60
        # This checks that the timer is completed, and on its final tick.
        if minutes == 0 and seconds == 0 and (self.time_tick / ScriptLoader.instance.GAME_TICK_RATE == elapsed.seconds):
            # Pause the game, and make it so that further tick increases don't update the timer text.
            World.instance.paused = True
            self.update_time_text = False
        ScriptLoader.instance.object_map["TimerText"].text = "{:02d}:{:02d}".format(minutes, seconds)

        for idx in range(len(self.bot_penalties)):
            if self.bot_penalties[idx] > 0:
                self.bot_penalties[idx] -= 1
                to_go = datetime.timedelta(seconds=self.bot_penalties[idx] / ScriptLoader.instance.GAME_TICK_RATE)
                ScriptLoader.instance.object_map[f"UI-penalty-{idx}"].children[0].visual.text = str(to_go.seconds)
                if self.bot_penalties[idx] == 0:
                    self.finishPenalty(idx)

        if self.out_on_white_tick > 0:
            self.out_on_white_tick -= 1
            if self.out_on_white_tick == 0:
                self.resetBallClosest()

    def goalScoredIn(self, teamIndex):
        self.team_scores[1 - teamIndex] += 1
        self.updateScoreText()
        self.resetPositions()
        # Pause the game temporarily
        World.instance.paused = True
        self.current_goal_score_tick = self.cur_tick
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team * self.BOTS_PER_TEAM + index
                if actual_index >= len(self.robots):
                    break
                ScriptLoader.instance.sendEvent(
                    f"Robot-{actual_index}", GOAL_SCORED, {"against_you": team == teamIndex}
                )

    def penaliseBot(self, botIndex):
        self.bot_penalties[botIndex] = self.BOT_OUT_ON_WHITE_PENALTY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
        self.robots[botIndex].clickable = False
        ScriptLoader.instance.sendEvent(f"Robot-{botIndex}", START_PENALTY, {})
        graphic = self.generatePenaltyGraphic(botIndex)

    def generatePenaltyGraphic(self, botIndex):
        team = botIndex // self.BOTS_PER_TEAM
        penaltyIndex = (
            len(
                [
                    x
                    for x in range(team * self.BOTS_PER_TEAM, (team + 1) * self.BOTS_PER_TEAM)
                    if x < len(self.bot_penalties) and self.bot_penalties[x] != 0
                ]
            )
            - 1
        )
        xPos = 128 if penaltyIndex == 0 else 115
        xPosMult = -1 if team == 0 else 1
        position = (xPos * xPosMult, 89)
        graphic_kwargs = {
            "type": "object",
            "collider": "inherit",
            "visual": {
                "name": "Rectangle",
                "width": 10,
                "height": 6,
                "fill": "penalty_ui_bg",
                "stroke": 0,
                "zPos": 5.5,
            },
            "children": [
                {
                    "type": "object",
                    "visual": {
                        "name": "Text",
                        "text": "x",
                        "fill": "UI_fg_2",
                        "font_size": 24,
                        "hAlignment": "m",
                        "vAlignment": "baseline",
                        "zPos": 5.6,
                    },
                    "position": [0, -2],
                    "key": f"UI-penalty-text-{botIndex}",
                }
            ],
            "position": position,
            "physics": True,
            "static": True,
            "key": f"UI-penalty-{botIndex}",
        }
        return ScriptLoader.instance.loadElements([graphic_kwargs])[0]

    def finishPenalty(self, botIndex):
        self.bot_penalties[botIndex] = 0
        self.robots[botIndex].clickable = True
        self.robots[botIndex].body.position = self.spawns[botIndex // self.BOTS_PER_TEAM][
            botIndex % self.BOTS_PER_TEAM
        ][0]
        self.robots[botIndex].body.angle = (
            self.spawns[botIndex // self.BOTS_PER_TEAM][botIndex % self.BOTS_PER_TEAM][1] * np.pi / 180
        )
        self.robots[botIndex].body.velocity = np.array([0.0, 0.0])
        self.robots[botIndex].body.angular_velocity = 0
        ScriptLoader.instance.sendEvent(f"Robot-{botIndex}", END_PENALTY, {})
        ScreenObjectManager.instance.unregisterVisual(f"UI-penalty-{botIndex}")
        ScreenObjectManager.instance.unregisterVisual(
            ScriptLoader.instance.object_map[f"UI-penalty-{botIndex}"].children[0].key
        )
        World.instance.unregisterObject(ScriptLoader.instance.object_map[f"UI-penalty-{botIndex}"])

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                for team in range(len(self.names)):
                    if shape.shape.obj.key.startswith(f"score{team+1}"):
                        action = shape.shape.obj.key.split(str(team + 1))[1]
                        if action == "Plus":
                            self.team_scores[team] += 1
                        elif action == "Minus":
                            if self.team_scores[team] > 0:
                                self.team_scores[team] -= 1
                        else:
                            raise ValueError(f"Unknown team action {action}")
                        self.updateScoreText()
                    for index in range(self.BOTS_PER_TEAM):
                        if team * self.BOTS_PER_TEAM + index < len(self.robots):
                            if shape.shape.obj.key == f"UI-penalty-{team * self.BOTS_PER_TEAM + index}":
                                self.finishPenalty(team * self.BOTS_PER_TEAM + index)
                if shape.shape.obj.key == "controlsReset":
                    self._pressed = True

        if event.type == pygame.MOUSEMOTION:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for team in range(len(self.names)):
                for index in range(self.BOTS_PER_TEAM):
                    for shape in shapes:
                        if shape.shape.obj.key == f"UI-penalty-{team * self.BOTS_PER_TEAM + index}":
                            shape.shape.obj.visual.fill = "penalty_ui_bg_hover"
                            break
                    else:
                        key = f"UI-penalty-{team * self.BOTS_PER_TEAM + index}"
                        if key in ScriptLoader.instance.object_map:
                            ScriptLoader.instance.object_map[key].visual.fill = "penalty_ui_bg"

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(m_pos, 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY))
            for shape in shapes:
                if (shape.shape.obj.key == "controlsReset") & self._pressed:
                    self.reset()
                self._pressed = False
            if len(shapes) == 0:
                self._pressed = False
