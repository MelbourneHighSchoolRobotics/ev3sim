import argparse
import sys
from collections import deque
from queue import Queue

parser = argparse.ArgumentParser(description='Run the simulation, include some robots and base it on a preset.')
parser.add_argument('--preset', type=str, help='Path of preset file to load.', default='presets/soccer.yaml', dest='preset')
parser.add_argument('robots', nargs='*', help='Path of robots to load.')

args = parser.parse_args(sys.argv[1:])

import yaml
from simulation.loader import runFromConfig

with open(args.preset, 'r') as f:
    config = yaml.safe_load(f)

config['robots'] = config.get('robots', []) + args.robots

shared_data = {
    'tick': 0,
    'write_stack': deque(),
    'data_queue': {},
    'active_count': {},
}

result_bucket = Queue(maxsize=1)

from threading import Thread
from simulation.communication import start_server_with_shared_data

def run(shared_data, result):
    try:
        runFromConfig(config, shared_data)
    except Exception as e:
        result.put(('Simulation', e))
        return
    result.put(True)

comm_thread = Thread(target=start_server_with_shared_data, args=(shared_data, result_bucket), daemon=True)
sim_thread = Thread(target=run, args=(shared_data, result_bucket), daemon=True)

comm_thread.start()
sim_thread.start()

try:
    with result_bucket.not_empty:
        while not result_bucket._qsize():
            result_bucket.not_empty.wait(1)
    r = result_bucket.get()
    if r is not True:
        print(f"An error occured in the {r[0]} thread. Raising an error now...")
        time.sleep(1)
        raise r[1]
except KeyboardInterrupt:
    pass
