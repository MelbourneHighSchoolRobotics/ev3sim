import argparse
import sys
import pygame
import yaml
from os import remove
from os.path import join, dirname, abspath, basename, isfile, sep

from ev3sim import __version__
from ev3sim.file_helper import WorkspaceError, find_abs, find_abs_directory
from ev3sim.search_locations import config_locations, preset_locations
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
    help="If specified, will begin the gui focusing on this file.",
)
parser.add_argument(
    "--open",
    action="store_true",
    help="Opens the current bot/sim file.",
    dest="open",
)
parser.add_argument(
    "--edit",
    action="store_true",
    help="Edits the current bot/sim file.",
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
        import platform
        import subprocess

        fname = join(ev3sim_folder, "user_config.yaml")

        if platform.system() == "Windows":
            subprocess.Popen(["explorer", "/select,", fname])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", fname])
        else:
            subprocess.Popen(["xdg-open", fname])
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
        # We have been given a file of some sort as an argument, figure out what it is and run with it.
        # First, figure out what type it is.
        if args.elem[-1] in "/\\":
            args.elem = args.elem[:-1]
        found = False

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

        from ev3sim.validation.batch_files import BatchValidator
        from ev3sim.validation.bot_files import BotValidator

        if not found:
            if BatchValidator.validate_file(args.elem):
                # Valid batch file.
                if args.open:
                    pushed_screens = [ScreenObjectManager.SCREEN_SIM]
                    pushed_kwargss = [
                        {
                            "batch": args.elem,
                        }
                    ]
                elif args.edit:
                    import importlib

                    with open(args.elem, "r") as f:
                        conf = yaml.safe_load(f)
                    with open(find_abs(conf["preset_file"], preset_locations())) as f:
                        preset = yaml.safe_load(f)
                    if "visual_settings" not in preset:
                        print("This preset cannot be edited.")
                        sys.exit(1)
                    mname, cname = preset["visual_settings"].rsplit(".", 1)
                    klass = getattr(importlib.import_module(mname), cname)

                    pushed_screens = [ScreenObjectManager.SCREEN_SETTINGS]
                    pushed_kwargss = [
                        {
                            "file": args.elem,
                            "settings": klass,
                            "allows_filename_change": True,
                            "extension": "sim",
                        }
                    ]
                found = True
            if not found:
                if BotValidator.validate_file(args.elem):
                    if args.open:
                        pushed_screens = [ScreenObjectManager.SCREEN_BOT_EDIT]
                        ignore = abspath(find_abs_directory("workspace"))
                        top_dir = abspath(dirname(args.elem))
                        pushed_kwargss = [
                            {
                                "bot_file": args.elem,
                                "bot_dir_file": ("workspace" + top_dir.replace(ignore, ""), basename(args.elem)),
                            }
                        ]
                    else:
                        print("Bot files cannot be opened for editing.")
                        sys.exit(1)
                    found = True

        if not found:
            print(f"Unsure what to do with file {args.elem}")
            sys.exit(1)

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
