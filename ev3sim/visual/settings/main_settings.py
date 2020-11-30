from ev3sim.visual.settings.elements import NumberEntry, FileEntry

main_settings = [
    {
        "height": (lambda s: 190 if s[0] < 580 else 140),
        "objects": [
            NumberEntry(["screen", "SCREEN_WIDTH"], 720, "Screen Width", (lambda s: (0, 20))),
            NumberEntry(
                ["screen", "SCREEN_HEIGHT"], 960, "Screen Height", (lambda s: (0, 70) if s[0] < 540 else (s[0] / 2, 20))
            ),
            NumberEntry(["app", "FPS"], 30, "FPS", (lambda s: (0, 120) if s[0] < 540 else (0, 70))),
        ],
    },
    {
        "height": (lambda s: 90),
        "objects": [
            FileEntry(["app", "workspace_folder"], None, "Workspace", (lambda s: (0, 20))),
        ],
    },
]