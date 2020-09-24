import argparse
import sys
import time
from random import randint, seed
from ev3sim.file_helper import find_abs

parser = argparse.ArgumentParser(description="Run the simulation, include some robots.")
parser.add_argument(
    "--preset",
    "-p",
    type=str,
    help="Path of preset file to load. (You shouldn't need to change this, by default it is presets/soccer.yaml)",
    default="soccer.yaml",
    dest="preset",
)
parser.add_argument("robots", nargs="*", help="Path of robots to load. Separate each robot path by a space.")
parser.add_argument(
    "--batch",
    "-b",
    action="store_true",
    help="Whether to use a batched command to run this simulation.",
    dest="batched",
)
parser.add_argument(
    "--bind_addr",
    default="[::1]:50051",
    metavar="address:port",
    help="The IP address and port to run on (you shouldn't need to change this). Default is [::1]:50051 (localhost only). Use [::]:50051 to listen on all network interfaces.",
)
parser.add_argument(
    "--seed",
    "-s",
    type=int,
    default=None,
    help="Used to seed randomisation, integer from 0 to 2^32-1. Will generate randomly if left blank.",
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
        passed_args = sys.argv

    args = parser.parse_args(passed_args[1:])

    if args.version:
        import ev3sim

        print(f"Running ev3sim version {ev3sim.__version__}")
        return

    if args.seed is None:
        seed(time.time())
        # Seed for numpy randomisation is 0 to 2^32-1, inclusive.
        args.seed = randint(0, (1 << 32) - 1)

    print(f"Simulating with seed {args.seed}")

    if args.batched:
        from ev3sim.batched_run import batched_run

        assert len(args.robots) == 1, "Exactly one batched command file should be provided."
        batched_run(args.robots[0], args.bind_addr, args.seed)
    else:
        from ev3sim.single_run import single_run

        assert len(args.robots) > 0, "Provide at least one bot to run the simulation with."
        single_run(args.preset, args.robots, args.bind_addr, args.seed)


if __name__ == "__main__":
    main()
