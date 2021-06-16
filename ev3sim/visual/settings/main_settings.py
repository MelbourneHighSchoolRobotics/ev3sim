from ev3sim.visual.settings.elements import NumberEntry, FileEntry, Checkbox

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
]
