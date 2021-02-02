import datetime
import pygame
import numpy as np
import math
import pymunk
from ev3sim.events import GOAL_SCORED, START_PENALTY, END_PENALTY
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory
from ev3sim.objects.utils import magnitude_sq
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.objects.base import DYNAMIC_CATEGORY, STATIC_CATEGORY
from ev3sim.settings import ObjectSetting


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

    TEAM_NAME_1 = ""
    TEAM_NAME_2 = ""
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

    # Don't autostart in the `startUp` parent call.
    AUTOSTART_BOTS = False

    _pressed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_goal_score_tick = -1
        self.out_on_white_tick = 0
        self.time_tick = 0
        self.update_time_text = True

    def startUp(self):
        super().startUp()
        self.START_TIME = datetime.timedelta(minutes=self.GAME_HALF_LENGTH_MINUTES)
        self.names = [self.TEAM_NAME_1, self.TEAM_NAME_2]
        self.spawns = self.SPAWN_LOCATIONS[:]
        self.penalty = self.PENALTY_LOCATIONS[:]
        self.goals = self.GOALS[:]
        assert len(self.names) == len(self.spawns) and len(self.spawns) == len(
            self.goals
        ), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.bot_penalties = [0] * len(self.robots)
        for i, bot in enumerate(self.robots):
            bot.shape.collision_type = self.BOT_COLLISION_TYPE
            bot.shape.bot_index = i
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

        saved_world_no = World.instance.spawn_no

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

        # Initialise field collider for ball reset on white
        self.field_ball = ScriptLoader.instance.object_map["centreFieldBallDetector"]
        self.field_ball.shape.sensor = True
        self.field_ball.shape.collision_type = self.FIELD_BALL_COLLISION_TYPE
        if self.BALL_RESET_ON_WHITE:
            handler = World.instance.space.add_collision_handler(
                self.FIELD_BALL_COLLISION_TYPE, self.BALL_COLLISION_TYPE
            )

            saved_world_no = World.instance.spawn_no

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

        # Initialise field collider for out on white
        self.field = ScriptLoader.instance.object_map["centreField"]
        self.field.shape.sensor = True
        self.field.shape.collision_type = self.FIELD_COLLISION_TYPE
        if self.ENFORCE_OUT_ON_WHITE:
            handler = World.instance.space.add_collision_handler(self.FIELD_COLLISION_TYPE, self.BOT_COLLISION_TYPE)

            saved_world_no = World.instance.spawn_no

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
            # Set up team name
            ScriptLoader.instance.object_map[f"name{x+1}Text"].text = self.names[x]
        for robot in self.robots:
            robot.robot_class.onSpawn()
        self.reset()

    def updateScoreText(self):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f"score{x+1}Text"].text = str(self.team_scores[x])

    def reset(self):
        self.team_scores = [0 for _ in self.names]
        self.updateScoreText()
        self.resetPositions()
        self.time_tick = 0
        self.update_time_text = True
        self.restartBots()

    def resetPositions(self):
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team + index * len(self.names)
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
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "ui/controls_reset_pressed.png"
        else:
            ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "ui/controls_reset_released.png"
        self.update_time()

    def afterPhysics(self):
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                actual_index = team + index * len(self.names)
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
                actual_index = team + index * len(self.names)
                if actual_index >= len(self.robots):
                    break
                ScriptLoader.instance.sendEvent(
                    f"Robot-{actual_index}", GOAL_SCORED, {"against_you": team == teamIndex}
                )

    def penaliseBot(self, botIndex):
        self.bot_penalties[botIndex] = self.BOT_OUT_ON_WHITE_PENALTY_SECONDS * ScriptLoader.instance.GAME_TICK_RATE
        self.robots[botIndex].clickable = False
        ScriptLoader.instance.sendEvent(f"Robot-{botIndex}", START_PENALTY, {})
        self.generatePenaltyGraphic(botIndex)

    def generatePenaltyGraphic(self, botIndex):
        team = botIndex % len(self.names)
        penaltyIndex = (
            len(
                [
                    team + x * len(self.names)
                    for x in range(self.BOTS_PER_TEAM)
                    if team + x * len(self.names) < len(self.bot_penalties)
                    and self.bot_penalties[team + x * len(self.names)] != 0
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
        self.robots[botIndex].body.position = self.spawns[botIndex % len(self.names)][botIndex // len(self.names)][0]
        self.robots[botIndex].body.angle = (
            self.spawns[botIndex // len(self.names)][botIndex % len(self.names)][1] * np.pi / 180
        )
        self.robots[botIndex].body.velocity = (0.0, 0.0)
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
            shapes = World.instance.space.point_query(
                [float(v) for v in m_pos], 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY)
            )
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
                        actual_index = team + index * len(self.names)
                        if actual_index < len(self.robots):
                            if shape.shape.obj.key == f"UI-penalty-{actual_index}":
                                self.finishPenalty(actual_index)
                if shape.shape.obj.key == "controlsReset":
                    self._pressed = True

        if event.type == pygame.MOUSEMOTION:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                [float(v) for v in m_pos], 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY)
            )
            for team in range(len(self.names)):
                for index in range(self.BOTS_PER_TEAM):
                    actual_index = team + index * len(self.names)
                    for shape in shapes:
                        if shape.shape.obj.key == f"UI-penalty-{team + index * len(self.names)}":
                            shape.shape.obj.visual.fill = "penalty_ui_bg_hover"
                            break
                    else:
                        key = f"UI-penalty-{team + index * len(self.names)}"
                        if key in ScriptLoader.instance.object_map:
                            ScriptLoader.instance.object_map[key].visual.fill = "penalty_ui_bg"

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                [float(v) for v in m_pos], 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY)
            )
            for shape in shapes:
                if (shape.shape.obj.key == "controlsReset") & self._pressed:
                    self.reset()
                self._pressed = False
            if len(shapes) == 0:
                self._pressed = False


soccer_settings = {
    attr: ObjectSetting(SoccerInteractor, attr)
    for attr in [
        "TEAM_NAME_1",
        "TEAM_NAME_2",
        "SPAWN_LOCATIONS",
        "PENALTY_LOCATIONS",
        "GOALS",
        "GAME_HALF_LENGTH_MINUTES",
        "SHOW_GOAL_COLLIDERS",
        "ENFORCE_OUT_ON_WHITE",
        "BALL_RESET_ON_WHITE",
        "BALL_RESET_WHITE_DELAY_SECONDS",
        "BOT_OUT_ON_WHITE_PENALTY_SECONDS",
    ]
}

from ev3sim.visual.settings.elements import NumberEntry, TextEntry, Checkbox

visual_settings = [
    {"height": lambda s: 90, "objects": [TextEntry("__filename__", "BATCH NAME", None, (lambda s: (0, 20)))]},
    {
        "height": lambda s: 190,
        "objects": [
            TextEntry(["settings", "soccer", "TEAM_NAME_1"], "Team 1", "Team 1 Name", (lambda s: (0, 20))),
            TextEntry(["settings", "soccer", "TEAM_NAME_2"], "Team 2", "Team 2 Name", (lambda s: (0, 70))),
            NumberEntry(["settings", "soccer", "GAME_HALF_LENGTH_MINUTES"], 5, "Halftime (m)", (lambda s: (0, 120))),
        ],
    },
    {
        "height": lambda s: 240 if s[0] < 580 else 140,
        "objects": [
            Checkbox(["settings", "soccer", "ENFORCE_OUT_ON_WHITE"], True, "Out on white", (lambda s: (0, 20))),
            Checkbox(
                ["settings", "soccer", "BALL_RESET_ON_WHITE"],
                True,
                "Ball reset on white",
                (lambda s: (0, 70) if s[0] < 540 else (s[0] / 2, 20)),
            ),
            NumberEntry(
                ["settings", "soccer", "BOT_OUT_ON_WHITE_PENALTY_SECONDS"],
                30,
                "Bot out penalty",
                (lambda s: (0, 120) if s[0] < 540 else (0, 70)),
            ),
            NumberEntry(
                ["settings", "soccer", "BALL_RESET_WHITE_DELAY_SECONDS"],
                5,
                "Ball reset delay",
                (lambda s: (0, 170) if s[0] < 540 else (s[0] / 2, 70)),
            ),
        ],
    },
]
