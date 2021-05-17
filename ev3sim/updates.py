"""Various functions for updating the workspace from earlier versions of ev3sim."""

import yaml
from ev3sim.settings import SettingsManager
from ev3sim.file_helper import ensure_workspace_filled, find_abs, find_abs_directory
from ev3sim.search_locations import config_locations


def check_for_bot_files():
    """v2.0.1 -> v2.1.0. Bots no longer config files, but folders with all information."""
    import os
    from ev3sim.file_helper import find_abs_directory
    from ev3sim.search_locations import asset_locations

    try:
        old_bots = []
        path = find_abs_directory("workspace/robots/")
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)) and file.endswith(".bot"):
                # Bad time
                old_bots.append(file)

        def action():
            import yaml

            """Go through and try fixing the bots."""
            for bot in old_bots:
                dirpath = os.path.join(path, bot[:-4])
                # Folder
                if os.path.isdir(dirpath):
                    import shutil

                    shutil.rmtree(dirpath)
                os.mkdir(dirpath)
                # config.bot
                with open(os.path.join(path, bot), "r") as f:
                    config = yaml.safe_load(f)
                bot_script = config.get("script", "code.py")
                preview_image = config.get("preview_path", "preview.png")
                for keyword in ["script", "preview_path"]:
                    if keyword in config:
                        del config[keyword]
                with open(os.path.join(dirpath, "config.bot"), "w") as f:
                    f.write(yaml.dump(config))
                # code.py
                try:
                    code_path = os.path.join(find_abs_directory("workspace/code/"), bot_script)
                    with open(code_path, "r") as f:
                        code = f.read()
                except:
                    code = ""
                with open(os.path.join(dirpath, "code.py"), "w") as f:
                    f.write(code)
                # preview.png
                try:
                    preview = find_abs(preview_image, asset_locations())
                    with open(preview, "rb") as f:
                        preview_data = f.read()
                except:
                    preview_data = bytes()
                with open(os.path.join(dirpath, "preview.png"), "wb") as f:
                    f.write(preview_data)
                # Remove the old bot
                os.remove(os.path.join(path, bot))
            # Additionally, we need to update all sim files to no longer use the .bot prefix
            actual_dir = find_abs_directory("workspace/sims/")
            for file in os.listdir(actual_dir):
                if os.path.isfile(os.path.join(actual_dir, file)) and file.endswith(".sim"):
                    with open(os.path.join(actual_dir, file), "r") as f:
                        config = yaml.safe_load(f)
                    for x in range(len(config.get("bots", []))):
                        if config["bots"][x].endswith(".bot"):
                            config["bots"][x] = config["bots"][x][:-4]
                    with open(os.path.join(actual_dir, file), "w") as f:
                        f.write(yaml.dump(config))

        if old_bots:
            return {
                "text": (
                    'Since you\'ve last used EV3Sim, the <font color="#4cc9f0">bot format</font> has changed.<br><br>'
                    + 'EV3Sim will now fix your current bots to use the new format (code and images will now appear in the <font color="#4cc9f0">bots</font> folder).'
                ),
                "type": "accept",
                "button": "Convert",
                "action": action,
            }
    except:
        pass
    return None


def check_for_sentry_preference():
    """First launch. User must select whether or not to send crashes to sentry."""
    from ev3sim.simulation.loader import StateHandler

    if StateHandler.SEND_CRASH_REPORTS is None:

        def action(result):
            SettingsManager.instance.setMany(
                {
                    "app": {
                        "send_crash_reports": result,
                    }
                }
            )
            # Change user_config to have workspace_folder = ""
            config_file = find_abs("user_config.yaml", config_locations())
            with open(config_file, "r") as f:
                conf = yaml.safe_load(f)
            conf["app"]["send_crash_reports"] = result
            with open(config_file, "w") as f:
                f.write(yaml.dump(conf))

        return {
            "text": "Send crash reports to make EV3Sim better?",
            "type": "boolean",
            "action": action,
        }


def fill_workspace():
    """Always ensure workspace has the necessary folders."""
    from ev3sim.simulation.loader import StateHandler

    if StateHandler.WORKSPACE_FOLDER:
        ensure_workspace_filled(find_abs_directory("workspace"))
    return None


UPDATE_CHECKS = [
    check_for_bot_files,
    check_for_sentry_preference,
    fill_workspace,
]


def handle_updates():
    """Returns a list of arguments to be passed in to the update dialog. If None is returned no updates need to be made."""

    res = []

    for update_method in UPDATE_CHECKS:
        r = update_method()
        if r is not None:
            res.append(r)

    return res
