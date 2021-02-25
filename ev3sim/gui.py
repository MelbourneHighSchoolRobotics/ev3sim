import argparse
import pygame
import sentry_sdk
import sys
import yaml
from os.path import join, split
from multiprocessing import Queue, Process

import ev3sim
from ev3sim.file_helper import find_abs, find_abs_directory
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


def main(passed_args=None):
    if passed_args is None:
        args = parser.parse_args(sys.argv[1:])
        # We are entering from main. Initialise sentry
        sentry_sdk.init(
            "https://847cb34de3b548bd9cf0ca4434ab02ed@o522431.ingest.sentry.io/5633878",
            release=ev3sim.__version__,
        )
    else:
        args = parser.parse_args([])
        args.__dict__.update(passed_args)

    pushed_screen = None
    pushed_kwargs = {}
    should_quit = False

    if not args.from_main:
        # Try loading a user config. If one does not exist, then generate one.
        try:
            conf_file = find_abs("user_config.yaml", allowed_areas=config_locations())
            with open(conf_file, "r") as f:
                conf = yaml.safe_load(f)
        except:
            with open(join(find_abs("default_config.yaml", ["package/presets/"])), "r") as fr:
                conf = yaml.safe_load(fr)
            with open(join(find_abs_directory(config_locations()[-1]), "user_config.yaml"), "w") as fw:
                fw.write(yaml.dump(conf))

        if args.config is not None:
            config_path = find_abs(args.config, allowed_areas=config_locations())
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            conf.update(config)

        handler = StateHandler()
        checkVersion()
        handler.setConfig(**conf)

        if args.elem:
            # First, figure out what type it is.
            from ev3sim.validation.batch_files import BatchValidator
            from ev3sim.validation.bot_files import BotValidator

            found = False
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

                        pushed_screen = ScreenObjectManager.SCREEN_SETTINGS
                        pushed_kwargs = {
                            "file": args.elem,
                            "settings": klass,
                            "allows_filename_change": True,
                            "extension": "sim",
                        }
                        found = True
            except:
                pass
            if not found:
                try:
                    fname = split(args.elem)[0]
                    for possible_dir in bot_locations():
                        dir_path = find_abs_directory(possible_dir, create=True)
                        if fname.startswith(dir_path):
                            fname = fname[len(dir_path) :]
                            fname = fname.replace("\\", "/")
                            break
                    bot_path = find_abs(fname, bot_locations())
                    if BotValidator.validate_file(bot_path):
                        if args.open:
                            pushed_screen = ScreenObjectManager.SCREEN_BOT_EDIT
                            for possible_dir in bot_locations():
                                try:
                                    n_bot_path = find_abs(fname, [possible_dir])
                                    pushed_kwargs = {
                                        "bot_file": n_bot_path,
                                        "bot_dir_file": (possible_dir, fname),
                                    }
                                    break
                                except:
                                    continue
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

    StateHandler.instance.startUp(push_screen=pushed_screen, push_kwargs=pushed_kwargs)

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

    try:
        StateHandler.instance.mainLoop()
    except Exception as e:
        import traceback, os

        print("An error occured in the Simulator :( Please see `error_log.txt` in your workspace.")
        actual_error = e
        error = traceback.format_exc()
        if os.path.exists(os.path.join(StateHandler.WORKSPACE_FOLDER, "error_log.txt")):
            os.remove(os.path.join(StateHandler.WORKSPACE_FOLDER, "error_log.txt"))
        with open(os.path.join(StateHandler.WORKSPACE_FOLDER, "error_log.txt"), "w") as f:
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
