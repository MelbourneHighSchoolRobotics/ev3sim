from ev3sim.validation.validator import Validator


class BotValidator(Validator):

    REQUIRED_KEYS = ["base_plate", "preview_path"]
    AVAILABLE_KEYS = REQUIRED_KEYS + ["devices", "robot_class", "script", "follow_collider"]

    @classmethod
    def validate_json(cls, json_obj) -> bool:
        return cls.validate_dict(json_obj)
