import argparse
import pygame
import requests
import sentry_sdk
import sys
import yaml
import os
import time
from multiprocessing import Queue, Process

import ev3sim
from ev3sim.file_helper import WorkspaceError, find_abs, find_abs_directory
from ev3sim.simulation.loader import StateHandler
from ev3sim.search_locations import batch_locations, bot_locations, config_locations, preset_locations
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.updates import handle_updates


def get_latest_version(q):
    try:
        from luddite import get_version_pypi

        v = get_version_pypi("ev3sim")
        q.put(v)
    except:
        q.put(ev3sim.__version__)


def checkVersion():
    Q = Queue()
    process = Process(target=get_latest_version, args=(Q,))
    process.start()
    process.join(2)
    if process.is_alive():
        process.terminate()
        ScreenObjectManager.NEW_VERSION = False
    else:
        ScreenObjectManager.NEW_VERSION = Q.get() != ev3sim.__version__


parser = argparse.ArgumentParser(description="Run the ev3sim graphical user interface.")
parser.add_argument(
    "elem",
    nargs="?",
    type=str,
    default=None,
    help="If specified, will begin the gui focusing on this file.",
)
parser.add_argument(
    "--config",
    "-c",
    type=str,
    default=None,
    help="Provide a file with some configurable values for the screen.",
)
parser.add_argument(
    "--from_main",
    action="store_true",
    help="This should only be set programmatically, if using the CLI then ignore.",
    dest="from_main",
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
    "--debug",
    action="store_true",
    help="Enable the debug interface",
    dest="debug",
)


def main(passed_args=None):
    if passed_args is None:
        args = parser.parse_args(sys.argv[1:])
    else:
        args = parser.parse_args([])
        args.__dict__.update(passed_args)

    if args.open_config:
        import platform
        import subprocess

        fname = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_config.yaml")

        if platform.system() == "Windows":
            subprocess.Popen(["explorer", "/select,", fname])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", fname])
        else:
            subprocess.Popen(["xdg-open", fname])
        return

    pushed_screens = []
    pushed_kwargss = [{}]
    should_quit = False

    if not args.from_main:
        # Try loading a user config. If one does not exist, then generate one.
        try:
            conf_file = find_abs("user_config.yaml", allowed_areas=config_locations())
            with open(conf_file, "r") as f:
                conf = yaml.safe_load(f)
        except:
            with open(os.path.join(find_abs("default_config.yaml", ["package/presets/"])), "r") as fr:
                conf = yaml.safe_load(fr)
            with open(os.path.join(find_abs_directory(config_locations()[-1]), "user_config.yaml"), "w") as fw:
                fw.write(yaml.dump(conf))

        if args.config is not None:
            config_path = find_abs(args.config, allowed_areas=config_locations())
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            conf.update(config)

        handler = StateHandler()
        checkVersion()
        handler.setConfig(**conf)

        if handler.SEND_CRASH_REPORTS:
            # We are entering from main. Initialise sentry
            sentry_sdk.init(
                "https://847cb34de3b548bd9cf0ca4434ab02ed@o522431.ingest.sentry.io/5633878",
                release=ev3sim.__version__,
            )

        if args.elem:
            # First, figure out what type it is.
            found = False
            if args.custom_url:
                from urllib.parse import urlparse
                import zipfile

                zip_url = args.elem.replace("ev3simc://", "https://")

                # Save the temp file here.
                c_path = os.path.dirname(__file__)
                fn = os.path.basename(urlparse(zip_url).path)
                fn = fn if fn.strip() else f"dload{str(int(time.time()))[:5]}"
                zip_path = c_path + os.path.sep + fn
                r = requests.get(zip_url, verify=True)
                with open(zip_path, "wb") as f:
                    f.write(r.content)

                extract_path = find_abs_directory("workspace/custom/")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    name = zip_ref.namelist()[0].split("\\")[0].split("/")[0]
                    zip_ref.extractall(extract_path)
                if os.path.isfile(zip_path):
                    os.remove(zip_path)
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

                        shutil.rmtree(os.path.join(extract_path, name))

                pushed_kwargss = [
                    {},
                    {"selected": os.path.join(extract_path, name, "sim.sim")},
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
                try:
                    if BatchValidator.validate_file(args.elem):
                        # Valid batch file.
                        if args.open:
                            from ev3sim.sim import main

                            args.batch = args.elem

                            should_quit = True
                            main(args.__dict__)
                            found = True
                            return
                        elif args.edit:
                            import importlib

                            with open(args.elem, "r") as f:
                                conf = yaml.safe_load(f)
                            with open(find_abs(conf["preset_file"], preset_locations())) as f:
                                preset = yaml.safe_load(f)
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
                except:
                    pass
                if not found:
                    try:
                        fname = os.path.split(args.elem)[0]
                        for possible_dir in bot_locations():
                            dir_path = find_abs_directory(possible_dir, create=True)
                            if fname.startswith(dir_path):
                                fname = fname[len(dir_path) :]
                                bot_path = os.path.join(dir_path, fname)
                                break
                        if BotValidator.validate_file(bot_path):
                            if args.open:
                                pushed_screens = [ScreenObjectManager.SCREEN_BOT_EDIT]
                                pushed_kwargss = [
                                    {
                                        "bot_file": bot_path,
                                        "bot_dir_file": (possible_dir, fname),
                                    }
                                ]
                            found = True
                    except:
                        pass

    if should_quit:
        # WHY DOES THIS HAPPEN?
        pygame.quit()
        StateHandler.instance.is_running = False
        try:
            StateHandler.instance.closeProcesses()
        except:
            pass
        raise ValueError(
            "Seems like something died :( Most likely the preset you are trying to load caused some issues."
        )

    try:
        StateHandler.instance.startUp(push_screens=pushed_screens, push_kwargss=pushed_kwargss)
    except WorkspaceError:
        pass

    if args.elem and args.from_main:
        args.simulation_kwargs.update(
            {
                "batch": args.elem,
            }
        )

        # We want to start on the simulation screen.
        ScreenObjectManager.instance.screen_stack = []
        ScreenObjectManager.instance.pushScreen(ScreenObjectManager.instance.SCREEN_SIM, **args.simulation_kwargs)

    updates = handle_updates()
    if updates:
        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.instance.SCREEN_UPDATE,
            panels=updates,
        )

    actual_error = None
    error = None

    if args.debug:
        try:
            import debugpy

            debugpy.listen(15995)
        except RuntimeError as e:
            print("Warning: Couldn't start the debugger")

    try:
        StateHandler.instance.mainLoop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback

        print("An error occured in the Simulator :( Please see `error_log.txt` in your workspace.")
        actual_error = e
        error = traceback.format_exc()
        if os.path.exists(os.path.join(StateHandler.WORKSPACE_FOLDER, "error_log.txt")):
            os.remove(os.path.join(StateHandler.WORKSPACE_FOLDER, "error_log.txt"))
        try:
            with open(os.path.join(StateHandler.WORKSPACE_FOLDER, "error_log.txt"), "w") as f:
                f.write(error)
        except FileNotFoundError:
            # If workspace is not defined, this might be useful.
            with open("error_log.txt", "w") as f:
                f.write(error)
    pygame.quit()
    StateHandler.instance.is_running = False
    try:
        StateHandler.instance.closeProcesses()
    except:
        pass
    if error is not None:
        raise actual_error


if __name__ == "__main__":
    main()
