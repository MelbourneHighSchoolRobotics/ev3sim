import argparse
import pygame

import yaml
from ev3sim.file_helper import find_abs
import sys
from ev3sim.simulation.loader import StateHandler

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
    default="screen_preset.yaml",
    help="Provide a file with some configurable values for the screen.",
)

def main(passed_args=None):
    if passed_args is None:
        args = parser.parse_args(sys.argv[1:])
    else:
        args = parser.parse_args([])
        args.__dict__.update(passed_args)
    
    config_path = find_abs(
        args.config, allowed_areas=["local", "local/presets/", "package", "package/presets/"]
    )
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    handler = StateHandler()
    handler.startUp(**config)

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
