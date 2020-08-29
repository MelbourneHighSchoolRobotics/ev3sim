import argparse
import sys
import time
from ev3sim.file_helper import find_abs

parser = argparse.ArgumentParser(description='Run the simulation, include some robots.')
parser.add_argument('--preset', '-p', type=str, help="Path of preset file to load. (You shouldn't need to change this, by default it is presets/soccer.yaml)", default='soccer.yaml', dest='preset')
parser.add_argument('robots', nargs='+', help='Path of robots to load. Separate each robot path by a space.')
parser.add_argument('--batch', '-b', action='store_true', help='Whether to use a batched command to run this simulation.', dest='batched')
parser.add_argument('--bind_addr', default='[::1]:50051', metavar='address:port', help="The IP address and port to run on (you shouldn't need to change this). Default is [::1]:50051 (localhost only). Use [::]:50051 to listen on all network interfaces.")

def main(passed_args = None):
    if passed_args is None:
        passed_args = sys.argv

    args = parser.parse_args(passed_args[1:])

    if args.batched:
        from ev3sim.batched_run import batched_run
        assert len(args.robots) == 1, "Exactly one batched command file should be provided."
        batched_run(args.robots[0], args.bind_addr)
    else:
        from ev3sim.single_run import single_run
        single_run(args.preset, args.robots, args.bind_addr)

if __name__ == '__main__':
    main()