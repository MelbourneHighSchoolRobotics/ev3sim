from ev3sim.file_helper import find_abs
from ev3sim.search_locations import config_locations
from ev3sim.visual.settings.elements import NumberEntry, FileEntry, Checkbox, Button
from ev3sim.visual.settings.randomisation_settings import randomisation_settings


def onClickConfigEditor(filename):
    from ev3sim.visual.manager import ScreenObjectManager

    ScreenObjectManager.instance.pushScreen(
        ScreenObjectManager.SCREEN_SETTINGS,
        file=find_abs("user_config.yaml", config_locations()),
        settings=randomisation_settings,
    )
    ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].clearEvents()


main_settings = [
    {
        "height": (lambda s: 240 if s[0] < 580 else 140),
        "objects": [
            NumberEntry(["screen", "SCREEN_WIDTH"], 720, "Screen Width", (lambda s: (0, 20)), int),
            NumberEntry(
                ["screen", "SCREEN_HEIGHT"],
                960,
                "Screen Height",
                (lambda s: (0, 70) if s[0] < 540 else (s[0] / 2, 20)),
                int,
            ),
            NumberEntry(["app", "FPS"], 30, "FPS", (lambda s: (0, 120) if s[0] < 540 else (0, 70)), int),
            Checkbox(["app", "console_log"], True, "Console", (lambda s: (0, 170) if s[0] < 540 else (s[0] / 2, 70))),
        ],
    },
    {
        "height": (lambda s: 90),
        "objects": [
            Checkbox(["app", "randomise_sensors"], False, "Random Noise", (lambda s: (0, 20))),
            Button("Randomisation Config", (lambda s: (0, 70) if s[0] < 540 else (s[0] / 2, 20)), onClickConfigEditor),
        ],
    },
    {
        "height": (lambda s: 90),
        "objects": [
            FileEntry(["app", "workspace_folder"], "", True, None, "Workspace", (lambda s: (0, 20))),
        ],
    },
]
