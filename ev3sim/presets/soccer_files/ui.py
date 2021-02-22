from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World
from ev3sim.visual.manager import ScreenObjectManager


class SoccerUIInteractor(IInteractor):

    # Must occur before device interactors.
    SORT_ORDER = -10
    instance = None

    SHOW_GOAL_COLLIDERS = True

    TEAM_NAME_1 = ""
    TEAM_NAME_2 = ""

    _pressed = False

    def __init__(self, **kwargs):
        SoccerUIInteractor.instance = self
        super().__init__(**kwargs)

    def startUp(self):
        super().startUp()
        self.names = [self.TEAM_NAME_1, self.TEAM_NAME_2]
        # Set up team name
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f"name{x+1}Text"].text = self.names[x]

    def updateScoreText(self, teamScores):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f"score{x+1}Text"].text = str(teamScores[x])

    def setPenaltyText(self, index, value):
        ScriptLoader.instance.object_map[f"UI-penalty-{index}"].children[0].visual.text = value

    def startPenalty(self, index, value):
        from ev3sim.presets.soccer_files.game_logic import SoccerLogicInteractor

        team = index % len(self.names)
        penaltyIndex = (
            len(
                [
                    team + x * len(self.names)
                    for x in range(SoccerLogicInteractor.instance.BOTS_PER_TEAM)
                    if team + x * len(self.names) < len(SoccerLogicInteractor.instance.bot_penalties)
                    and SoccerLogicInteractor.instance.bot_penalties[team + x * len(self.names)] != 0
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
                        "text": value,
                        "fill": "UI_fg_2",
                        "font_size": 24,
                        "hAlignment": "m",
                        "vAlignment": "baseline",
                        "zPos": 5.6,
                    },
                    "position": [0, -2],
                    "key": f"UI-penalty-text-{index}",
                }
            ],
            "position": position,
            "physics": True,
            "static": True,
            "key": f"UI-penalty-{index}",
        }
        return ScriptLoader.instance.loadElements([graphic_kwargs])[0]

    def endPenalty(self, index):
        ScreenObjectManager.instance.unregisterVisual(f"UI-penalty-{index}")
        ScreenObjectManager.instance.unregisterVisual(f"UI-penalty-{index}-child-0")
        World.instance.unregisterObject(ScriptLoader.instance.object_map[f"UI-penalty-{index}"])

    def onResetPressed(self):
        self._pressed = True
        ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "ui/controls_reset_pressed.png"

    def onResetReleased(self, hovered):
        if hovered and self._pressed:
            from ev3sim.presets.soccer_files.game_logic import SoccerLogicInteractor

            SoccerLogicInteractor.instance.reset()
        self._pressed = False
        ScriptLoader.instance.object_map["controlsReset"].visual.image_path = "ui/controls_reset_released.png"
