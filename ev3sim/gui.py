import argparse
import pygame
import sys
import yaml
from os.path import join

from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.simulation.loader import StateHandler
from ev3sim.search_locations import config_locations

parser = argparse.ArgumentParser(description="Run the ev3sim graphical user interface.")
parser.add_argument(
    "--batch",
    "-b",
    type=str,
    default=None,
    help="If specified, will begin the gui simulating a particular batch file.",
)
parser.add_argument(
    "--config",
    "-c",
    type=str,
    default=None,
    help="Provide a file with some configurable values for the screen.",
)


def main(passed_args=None):
    if passed_args is None:
        args = parser.parse_args(sys.argv[1:])
    else:
        args = parser.parse_args([])
        args.__dict__.update(passed_args)

    # Try loading a user config. If one does not exist, then generate one.
    try:
        conf_file = find_abs("user_config.yaml", allowed_areas=config_locations)
        with open(conf_file, "r") as f:
            conf = yaml.safe_load(f)
    except:
        with open(join(find_abs("default_config.yaml", ["package/presets/"])), "r") as fr:
            conf = yaml.safe_load(fr)
        with open(join(find_abs_directory(config_locations[-1]), "user_config.yaml"), "w") as fw:
            fw.write(yaml.dump(conf))

    if args.config is not None:
        config_path = find_abs(args.config, allowed_areas=config_locations)
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        conf.update(config)

    handler = StateHandler()
    handler.startUp(**conf)

    if args.batch:
        handler.beginSimulation(args.simulation_kwargs)

    error = None

    try:
        handler.mainLoop()
    except Exception as e:
        print("An error occured in the Simulator :(")
        error = e
    pygame.quit()
    handler.is_running = False
    try:
        handler.closeProcesses()
    except:
        pass
    if error is not None:
        raise error


if __name__ == "__main__":
    main()
