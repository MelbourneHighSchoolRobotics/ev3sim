from ev3sim.simulation.loader import ScriptLoader, StateHandler, initialiseFromConfig
from ev3sim.simulation.randomisation import Randomiser
import yaml
from ev3sim.file_helper import find_abs
from ev3sim.utils import Queue, recursive_merge
from ev3sim.search_locations import preset_locations, batch_locations


def simulate(batch_file, preset_filename, bot_paths, seed, override_settings, *queues_sizes):
    result_queue = queues_sizes[0][0]
    result_queue._internal_size = queues_sizes[0][1]
    StateHandler.instance.shared_info = {
        "result_queue": result_queue,
    }
    send_queues = [q for q, _ in queues_sizes[1::2]]
    for i, (_, size) in enumerate(queues_sizes[1::2]):
        send_queues[i]._internal_size = size
    recv_queues = [q for q, _ in queues_sizes[2::2]]
    for i, (_, size) in enumerate(queues_sizes[2::2]):
        recv_queues[i]._internal_size = size

    Randomiser.createGlobalRandomiserWithSeed(seed)

    preset_file = find_abs(preset_filename, allowed_areas=preset_locations())
    with open(preset_file, "r") as f:
        config = yaml.safe_load(f)
    config["settings"] = config.get("settings", {})
    recursive_merge(config["settings"], override_settings)

    config["robots"] = config.get("robots", []) + bot_paths

    initialiseFromConfig(config, send_queues, recv_queues)


def batched_run(batch_file, seed):

    with open(batch_file, "r") as f:
        config = yaml.safe_load(f)

    bot_paths = [x for x in config["bots"]]
    sim_args = [batch_file, config["preset_file"], bot_paths, seed, config.get("settings", {})]
    queues = [Queue() for _ in range(2 * len(bot_paths) + 1)]
    queue_with_count = [(q, q._internal_size) for q in queues]

    sim_args.extend(queue_with_count)

    ScriptLoader.instance.reset()
    ScriptLoader.instance.startUp()

    # Begin the sim process.
    simulate(*sim_args)
