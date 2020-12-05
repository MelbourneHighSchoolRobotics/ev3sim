from queue import Empty
from ev3sim.simulation.loader import StateHandler, initialiseFromConfig
from ev3sim.simulation.randomisation import Randomiser
import yaml
import time
from ev3sim.file_helper import find_abs
from multiprocessing import Process
from ev3sim.utils import Queue, recursive_merge
from ev3sim.search_locations import preset_locations, batch_locations, bot_locations, code_locations


def simulate(batch_file, preset_filename, bot_paths, seed, override_settings, bot_processes, *queues_sizes):
    result_queue = queues_sizes[0][0]
    result_queue._internal_size = queues_sizes[0][1]
    StateHandler.instance.shared_info = {
        "result_queue": result_queue,
        "processes": bot_processes,
    }
    send_queues = [q for q, _ in queues_sizes[1::2]]
    for i, (_, size) in enumerate(queues_sizes[1::2]):
        send_queues[i]._internal_size = size
    recv_queues = [q for q, _ in queues_sizes[2::2]]
    for i, (_, size) in enumerate(queues_sizes[2::2]):
        recv_queues[i]._internal_size = size

    Randomiser.createGlobalRandomiserWithSeed(seed)

    preset_file = find_abs(preset_filename, allowed_areas=preset_locations)
    with open(preset_file, "r") as f:
        config = yaml.safe_load(f)
    recursive_merge(config["settings"], override_settings)

    config["robots"] = config.get("robots", []) + bot_paths

    initialiseFromConfig(config, send_queues, recv_queues)


def batched_run(batch_file, bind_addr, seed):

    batch_path = find_abs(batch_file, allowed_areas=batch_locations)
    with open(batch_path, "r") as f:
        config = yaml.safe_load(f)

    bot_paths = [x for x in config["bots"]]
    sim_args = [batch_file, config["preset_file"], bot_paths, seed, config.get("settings", {})]
    queues = [Queue() for _ in range(2 * len(bot_paths) + 1)]
    queue_with_count = [(q, q._internal_size) for q in queues]
    result_queue = queues[0]

    from ev3sim.attach_bot import attach_bot

    bot_processes = []
    for i, bot in enumerate(bot_paths):
        p = find_abs(bot, allowed_areas=bot_locations)
        with open(p, "r") as f:
            conf = yaml.safe_load(f)
        if conf.get("script", None) is not None:
            fname = find_abs(conf["script"], allowed_areas=code_locations)
            bot_processes.append(
                Process(
                    target=attach_bot,
                    args=(
                        f"Robot-{i}",
                        fname,
                        result_queue,
                        result_queue._internal_size,
                        queues[2 * i + 1],
                        queues[2 * i + 1]._internal_size,
                        queues[2 * i + 2],
                        queues[2 * i + 2]._internal_size,
                    ),
                )
            )
    sim_args.append(bot_processes)
    sim_args.extend(queue_with_count)

    # Begin the sim process.
    simulate(*sim_args)
    for p in bot_processes:
        p.start()
