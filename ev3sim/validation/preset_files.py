from ev3sim.validation.validator import Validator


class PresetValidator(Validator):

    REQUIRED_KEYS = ["interactors", "elements"]
    # Most of these keys are required if the preset is not "hidden".
    AVAILABLE_KEYS = REQUIRED_KEYS + [
        "preview_path",
        "button_bg",
        "bot_names",
        "visual_settings",
        "preset_description",
        "colours",
        "settings",
        "hidden",
    ]

    @classmethod
    def validate_json(cls, json_obj) -> bool:
        return cls.validate_dict(json_obj)
