from ev3sim.presets.soccer_files.game_logic import SoccerLogicInteractor
from ev3sim.presets.soccer_files.ui import SoccerUIInteractor
from ev3sim.settings import ObjectSetting


soccer_settings = {
    attr: ObjectSetting(klass, attr)
    for attr, klass in [
        ("TEAM_NAME_1", SoccerUIInteractor),
        ("TEAM_NAME_2", SoccerUIInteractor),
        ("SHOW_GOAL_COLLIDERS", SoccerUIInteractor),
        ("SPAWN_LOCATIONS", SoccerLogicInteractor),
        ("PENALTY_LOCATIONS", SoccerLogicInteractor),
        ("GOALS", SoccerLogicInteractor),
        ("GAME_HALF_LENGTH_MINUTES", SoccerLogicInteractor),
        ("ENFORCE_OUT_ON_WHITE", SoccerLogicInteractor),
        ("BALL_RESET_ON_WHITE", SoccerLogicInteractor),
        ("BALL_RESET_WHITE_DELAY_SECONDS", SoccerLogicInteractor),
        ("BOT_OUT_ON_WHITE_PENALTY_SECONDS", SoccerLogicInteractor),
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
            NumberEntry(
                ["settings", "soccer", "GAME_HALF_LENGTH_MINUTES"], 5, "Halftime (m)", (lambda s: (0, 120)), float
            ),
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
                float,
            ),
            NumberEntry(
                ["settings", "soccer", "BALL_RESET_WHITE_DELAY_SECONDS"],
                5,
                "Ball reset delay",
                (lambda s: (0, 170) if s[0] < 540 else (s[0] / 2, 70)),
                float,
            ),
        ],
    },
]
