import argparse
import sys
import pygame
import yaml
from os import remove
from os.path import join, dirname, abspath, basename, isfile, sep, exists, relpath

from ev3sim import __version__
import ev3sim
from ev3sim.file_helper import WorkspaceError, find_abs, find_abs_directory, make_relative
from ev3sim.search_locations import bot_locations, config_locations, preset_locations
from ev3sim.simulation.loader import StateHandler
from ev3sim.updates import handle_updates
from ev3sim.utils import checkVersion
from ev3sim.visual.manager import ScreenObjectManager

parser = argparse.ArgumentParser(description="Run the ev3sim graphical user interface.")
parser.add_argument(
    "elem",
    nargs="?",
    type=str,
    default=None,
    help="""If specified, will try to open this file for use in ev3sim. Valid selections are:
    - Python files, separate from bots (open / edit)
    - Python files, located within bots (open / edit)
    - Bot folders / config.bot files (open / sometimes edit)
    - Simulation preset files (.sim) (open / sometimes edit)
    - Custom task folders (open)
""",
)
parser.add_argument(
    "--edit",
    action="store_true",
    help="Provided 'elem' is given, Edits the 'elem', rather than opening it.",
    dest="edit",
)
parser.add_argument(
    "--custom-url",
    action="store_true",
    help="Downloads and installs a custom task",
    dest="custom_url",
)
parser.add_argument(
    "--open_user_config",
    action="store_true",
    help="Debug tool to open the user_config file",
    dest="open_config",
)
parser.add_argument(
    "--no-debug",
    action="store_false",
    help="Disables the debug interface",
    dest="debug",
)
parser.add_argument(
    "--version",
    "-v",
    action="store_true",
    help="Show the version of ev3sim.",
    dest="version",
)


def raise_error(error_message):
    return [ScreenObjectManager.SCREEN_UPDATE], [
        {
            "panels": [
                {
                    "text": error_message,
                    "type": "accept",
                    "button": "Close",
                    "action": None,
                }
            ]
        }
    ]


def run_bot(bot_folder, script_name=None, edit=False):
    from ev3sim.validation.bot_files import BotValidator

    if not exists(join(bot_folder, "config.bot")):
        return raise_error(
            f"The bot {bot_folder} has been messed with, it is missing config.bot. If it has been deleted, please put it back there."
        )

    with open(join(bot_folder, "config.bot"), "r") as f:
        config = yaml.safe_load(f)
    if script_name is not None:
        config["script"] = script_name
        config["type"] = "mindstorms" if script_name.endswith(".ev3") else "python"
        with open(join(bot_folder, "config.bot"), "w") as f:
            f.write(yaml.dump(config))

    if not BotValidator.validate_file(bot_folder):
        return raise_error(f"There is something wrong with the robot {bot_folder}, and so it cannot be opened or used.")

    try:
        relative_dir, relative_path = make_relative(bot_folder, ["workspace"])
        if relative_path.startswith("robots"):
            raise ValueError()
        sim_paths = [join(dirname(bot_folder), "sim.sim")]
    except:
        relative_dir, relative_path = make_relative(bot_folder, bot_locations())
        sim_paths = [
            find_abs("presets/soccer.sim", ["package"]),
            find_abs("presets/rescue.sim", ["package"]),
        ]

    if not edit:
        found = False
        for sim in sim_paths:
            with open(sim, "r") as f:
                config = yaml.safe_load(f)
            for botpath in config["bots"]:
                if botpath == relative_path:
                    found = True
                    break
            if found:
                return run_sim(sim)
        # Not in the predefined presets.
        # Use the testing preset.
        sim_path = find_abs("presets/testing.sim", ["package"])
        with open(sim_path, "r") as f:
            test_config = yaml.safe_load(f)

        test_config["bots"] = [relative_path]
        with open(sim_path, "w") as f:
            f.write(yaml.dump(test_config))

        return run_sim(sim_path)
    else:
        return [ScreenObjectManager.SCREEN_BOT_EDIT], [
            {
                "bot_file": bot_folder,
                "bot_dir_file": (relative_dir, relative_path),
            }
        ]


def run_code(script_name):
    real = find_abs("examples/robots/default_testing", ["package"])
    rel_dir, rel_path = make_relative(real, bot_locations())
    with open(join(real, "config.bot"), "r") as f:
        bot_config = yaml.safe_load(f)
    bot_config["script"] = script_name
    bot_config["type"] = "mindstorms" if script_name.endswith(".ev3") else "python"
    with open(join(real, "config.bot"), "w") as f:
        f.write(yaml.dump(bot_config))

    sim_path = find_abs("presets/testing.sim", ["package"])
    with open(sim_path, "r") as f:
        test_config = yaml.safe_load(f)

    test_config["bots"] = [rel_path]
    with open(sim_path, "w") as f:
        f.write(yaml.dump(test_config))

    return run_sim(sim_path)


def run_sim(sim_path, edit=False):
    from ev3sim.validation.batch_files import BatchValidator

    if not BatchValidator.validate_file(sim_path):
        return raise_error(f"There is something wrong with the sim {sim_path}, and so it cannot be opened or used.")
    if not edit:
        return [ScreenObjectManager.SCREEN_SIM], [
            {
                "batch": sim_path,
            }
        ]
    import importlib

    with open(sim_path, "r") as f:
        conf = yaml.safe_load(f)
    with open(find_abs(conf["preset_file"], preset_locations())) as f:
        preset = yaml.safe_load(f)
    if "visual_settings" not in preset:
        return raise_error("This preset cannot be edited.")
    mname, cname = preset["visual_settings"].rsplit(".", 1)
    klass = getattr(importlib.import_module(mname), cname)

    return [ScreenObjectManager.SCREEN_SETTINGS], [
        {
            "file": sim_path,
            "settings": klass,
            "allows_filename_change": True,
            "extension": "sim",
        }
    ]


def main(passed_args=None):
    if passed_args is None:
        args = parser.parse_args(sys.argv[1:])
    else:
        # Just give some generic input
        args = parser.parse_args(["blank.yaml"])
        args.__dict__.update(passed_args)

    # Useful for a few things.
    ev3sim_folder = dirname(abspath(__file__))

    # Step 1: Handling helper commands

    if args.version:
        import ev3sim

        print(f"Running ev3sim version {ev3sim.__version__}")
        return

    if args.open_config:
        from ev3sim.utils import open_file, APP_EXPLORER

        fname = join(ev3sim_folder, "user_config.yaml")
        open_file(fname, APP_EXPLORER)
        return

    # Step 2: Safely load configs and set up error reporting

    try:
        # This should always exist.
        conf_file = find_abs("user_config.yaml", allowed_areas=config_locations())
        with open(conf_file, "r") as f:
            conf = yaml.safe_load(f)

        handler = StateHandler()
        checkVersion()
        handler.setConfig(**conf)
        # If no workspace has been set, place it in the package directory.
        if not handler.WORKSPACE_FOLDER:
            handler.setConfig(
                **{
                    "app": {
                        "workspace_folder": find_abs_directory("package/workspace", create=True),
                    }
                }
            )
    except Exception as e:
        import traceback as tb

        error = "".join(tb.format_exception(None, e, e.__traceback__))
        with open(join(ev3sim_folder, "error_log.txt"), "w") as f:
            f.write(error)
        print(f"An error occurred before sentry could load, check {join(ev3sim_folder, 'error_log.txt')}")
        sys.exit(1)

    if handler.SEND_CRASH_REPORTS:
        import sentry_sdk

        sentry_sdk.init(
            "https://847cb34de3b548bd9cf0ca4434ab02ed@o522431.ingest.sentry.io/5633878",
            release=__version__,
        )

    # Step 3: Identify what screens we need to show and start up any other processes

    pushed_screens = []
    pushed_kwargss = [{}]
    if args.elem:
        # We have been given a path of some sort as an argument, figure out what it is and run with it.
        # First, figure out what type it is.
        if args.elem[-1] in "/\\":
            args.elem = args.elem[:-1]

        if args.custom_url:
            import time
            import requests
            import zipfile
            from urllib.parse import urlparse

            zip_url = args.elem.replace("ev3simc://", "https://")

            # Save the temp file here.
            c_path = dirname(__file__)
            fn = basename(urlparse(zip_url).path)
            fn = fn if fn.strip() else f"dload{str(int(time.time()))[:5]}"
            zip_path = c_path + sep + fn
            r = requests.get(zip_url, verify=True)
            with open(zip_path, "wb") as f:
                f.write(r.content)

            extract_path = find_abs_directory("workspace/custom/")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                name = zip_ref.namelist()[0].split("\\")[0].split("/")[0]
                zip_ref.extractall(extract_path)
            if isfile(zip_path):
                remove(zip_path)
            found = True
            pushed_screens = [
                ScreenObjectManager.SCREEN_MENU,
                ScreenObjectManager.SCREEN_BATCH,
                ScreenObjectManager.SCREEN_UPDATE,
            ]

            def action(result):
                if not result:
                    # Delete
                    import shutil

                    shutil.rmtree(join(extract_path, name))

            pushed_kwargss = [
                {},
                {"selected": join(extract_path, name, "sim.sim")},
                {
                    "panels": [
                        {
                            "type": "boolean",
                            "text": (
                                "Custom tasks downloaded from the internet can do <i>anything</i> to your computer."
                                " Only use custom tasks from a developer you <b>trust</b>."
                            ),
                            "button_yes": "Accept",
                            "button_no": "Delete",
                            "action": action,
                        }
                    ]
                },
            ]

        elif not exists(args.elem):
            pushed_screens, pushed_kwargss = raise_error(f"Unknown path {args.elem}.")
        elif args.elem.endswith(".py") or args.elem.endswith(".ev3"):
            # Python file, either in bot or completely separate.
            folder = dirname(args.elem)
            config_path = join(folder, "config.bot")
            if exists(config_path):
                # We are in a bot directory.
                pushed_screens, pushed_kwargss = run_bot(folder, basename(args.elem), edit=args.edit)
            else:
                pushed_screens, pushed_kwargss = run_code(args.elem)
        elif args.elem.endswith(".bot"):
            # Bot file.
            folder = dirname(args.elem)
            pushed_screens, pushed_kwargss = run_bot(folder, edit=args.edit)
        elif args.elem.endswith(".sim"):
            pushed_screens, pushed_kwargss = run_sim(args.elem, edit=args.edit)
        else:
            # Some sort of folder. Either a bot folder, or custom task folder.
            config_path = join(args.elem, "config.bot")
            sim_path = join(args.elem, "sim.sim")
            if exists(config_path):
                pushed_screens, pushed_kwargss = run_bot(args.elem, edit=args.edit)
            elif exists(sim_path):
                pushed_screens, pushed_kwargss = run_sim(sim_path, edit=args.edit)
            else:
                pushed_screens, pushed_kwargss = raise_error(
                    f"EV3Sim does not know how to open {args.elem}{' for editing' if args.edit else ''}."
                )

    try:
        StateHandler.instance.startUp(push_screens=pushed_screens, push_kwargss=pushed_kwargss)
    except WorkspaceError:
        pass

    updates = handle_updates()
    if updates:
        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.instance.SCREEN_UPDATE,
            panels=updates,
        )

    if args.debug:
        try:
            import debugpy

            debugpy.listen(15995)
        except RuntimeError as e:
            print("Warning: Couldn't start the debugger")

    # Step 4: Mainloop

    try:
        handler.mainLoop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback as tb

        error = "".join(tb.format_exception(None, e, e.__traceback__))
        with open(join(ev3sim_folder, "error_log.txt"), "w") as f:
            f.write(error)
        print(f"An error occurred, check {join(ev3sim_folder, 'error_log.txt')} for details.")

    pygame.quit()
    handler.is_running = False
    try:
        handler.closeProcesses()
    except:
        pass


if __name__ == "__main__":
    main()
