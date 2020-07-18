import argparse
import sys

parser = argparse.ArgumentParser(description='Run the simulation, include some robots and base it on a preset.')
parser.add_argument('--preset', type=str, help='Path of preset file to load.', default='presets/soccer.yaml', dest='preset')
parser.add_argument('robots', nargs='*', help='Path of robots to load.')

args = parser.parse_args(sys.argv[1:])

import yaml
from simulation.loader import runFromConfig

with open(args.preset, 'r') as f:
    config = yaml.safe_load(f)

config['robots'] = config.get('robots', []) + args.robots

runFromConfig(config)