from ev3sim.validation.validator import Validator


class BotValidator(Validator):

    FILE_EXT = "bot"

    REQUIRED_KEYS = ["base_plate", "preview_path"]
    AVAILABLE_KEYS = REQUIRED_KEYS + ["devices", "robot_class", "script", "follow_collider", "hidden", "hidden_edit"]

    @classmethod
    def validate_json(cls, json_obj) -> bool:
        return cls.validate_dict(json_obj)
