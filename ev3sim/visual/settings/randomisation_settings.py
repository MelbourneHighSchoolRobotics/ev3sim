from ev3sim.visual.settings.elements import NumberEntry, Title

randomisation_settings = [
    {
        "height": (lambda s: 290 if s[0] < 580 else 190),
        "objects": [
            Title("Colour Sensor", (lambda s: (0, 20))),
            NumberEntry(["randomisation", "COLOUR_SENSOR_RADIUS"], 1, "Sampling Radius", (lambda s: (0, 70)), float),
            NumberEntry(
                ["randomisation", "COLOUR_SENSOR_SAMPLING_POINTS"],
                100,
                "Sampling Points",
                (lambda s: (0, 120) if s[0] < 540 else (s[0] / 2, 70)),
                int,
            ),
            NumberEntry(
                ["randomisation", "COLOUR_MAX_RGB_BIAS"],
                400,
                "Max RGB Bias",
                (lambda s: (0, 170) if s[0] < 540 else (0, 120)),
                float,
            ),
            NumberEntry(
                ["randomisation", "COLOUR_MIN_RGB_BIAS"],
                230,
                "Min RGB Bias",
                (lambda s: (0, 220) if s[0] < 540 else (s[0] / 2, 120)),
                float,
            ),
        ],
    },
    {
        "height": (lambda s: 340 if s[0] < 580 else 240),
        "objects": [
            Title("Compass Sensor", (lambda s: (0, 20))),
            NumberEntry(["randomisation", "COMPASS_N_POINTS"], 51, "Static Points", (lambda s: (0, 70)), int),
            NumberEntry(
                ["randomisation", "COMPASS_POINT_VARIANCE"],
                16,
                "Static Variance",
                (lambda s: (0, 120) if s[0] < 540 else (s[0] / 2, 70)),
                float,
            ),
            NumberEntry(
                ["randomisation", "COMPASS_NOISE_RATE"],
                0.03,
                "Noise rate of change",
                (lambda s: (0, 170) if s[0] < 540 else (0, 120)),
                float,
            ),
            NumberEntry(
                ["randomisation", "COMPASS_NOISE_AMP"],
                0.2,
                "Noise amplitude",
                (lambda s: (0, 220) if s[0] < 540 else (s[0] / 2, 120)),
                float,
            ),
            NumberEntry(
                ["randomisation", "COMPASS_MAXIMUM_NOISE_EFFECT"],
                15,
                "Max Noise effect",
                (lambda s: (0, 270) if s[0] < 540 else (0, 170)),
                float,
            ),
        ],
    },
    {
        "height": (lambda s: 140),
        "objects": [
            Title("Infrared Sensor", (lambda s: (0, 20))),
            NumberEntry(["randomisation", "INFRARED_BIAS_AMP"], 5, "Bias Amplitude", (lambda s: (0, 70)), float),
        ],
    },
    {
        "height": (lambda s: 190 if s[0] < 580 else 140),
        "objects": [
            Title("Ultrasonic Sensor", (lambda s: (0, 20))),
            NumberEntry(
                ["randomisation", "ULTRASONIC_NOISE_ANGLE_AMPLITUDE"],
                40,
                "Angle change effect",
                (lambda s: (0, 70)),
                float,
            ),
            NumberEntry(
                ["randomisation", "ULTRASONIC_OFFSET_AMP"],
                5,
                "Static noise",
                (lambda s: (0, 120) if s[0] < 540 else (s[0] / 2, 70)),
                float,
            ),
        ],
    },
    {
        "height": (lambda s: 240 if s[0] < 580 else 190),
        "objects": [
            Title("Motors", (lambda s: (0, 20))),
            NumberEntry(["randomisation", "MOTOR_MIN_MULT"], 0.9, "Min speed mult", (lambda s: (0, 70)), float),
            NumberEntry(
                ["randomisation", "MOTOR_MAX_MULT"],
                1.05,
                "Max speed mult",
                (lambda s: (0, 120) if s[0] < 540 else (s[0] / 2, 70)),
                float,
            ),
            NumberEntry(
                ["randomisation", "MOTOR_N_SPEEDS"],
                71,
                "Static Points",
                (lambda s: (0, 170) if s[0] < 540 else (0, 120)),
                int,
            ),
        ],
    },
]
