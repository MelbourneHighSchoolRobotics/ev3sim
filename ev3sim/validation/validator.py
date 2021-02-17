import os
import yaml


class Validator:

    FILE_EXT = "yaml"
    # Abstract methods

    @classmethod
    def validate_json(cls, json_obj) -> bool:
        raise NotImplementedError()

    @classmethod
    def validate_file(cls, filepath) -> bool:
        try:
            if os.path.isdir(filepath):
                return False
            if filepath.endswith(f".{cls.FILE_EXT}"):
                with open(filepath, "r") as f:
                    config = yaml.safe_load(f)
                    return cls.validate_json(config)
        except:
            return False
        return False

    @classmethod
    def all_valid_in_dir(cls, dirpath):
        """Check for valid files in a specific directory. This is NOT recursive by design."""
        for path in os.listdir(dirpath):
            total = os.path.join(dirpath, path)
            if cls.validate_file(total):
                yield path

    # Methods for json parsing where JSON is dict.

    REQUIRED_KEYS = []
    AVAILABLE_KEYS = []

    @classmethod
    def validate_dict(cls, json_obj) -> bool:
        if not isinstance(json_obj, dict):
            return False
        for key in cls.REQUIRED_KEYS:
            if key not in json_obj:
                return False
        for key in json_obj:
            if key not in cls.AVAILABLE_KEYS:
                return False
        # We have all required keys, and all keys in the yaml are expected. This is ok.
        return True
