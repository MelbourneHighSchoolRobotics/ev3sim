from ev3sim.validation.validator import Validator


class BotValidator(Validator):

    FILE_EXT = "bot"

    REQUIRED_KEYS = ["base_plate"]
    AVAILABLE_KEYS = REQUIRED_KEYS + [
        "devices",
        "robot_class",
        "script",
        "preview_path",
        "follow_collider",
        "hidden",
        "hidden_edit",
        "type",
    ]

    @classmethod
    def validate_file(cls, filepath):
        from os.path import join

        return super().validate_file(join(filepath, "config.bot"))

    @classmethod
    def validate_json(cls, json_obj) -> bool:
        return cls.validate_dict(json_obj)
