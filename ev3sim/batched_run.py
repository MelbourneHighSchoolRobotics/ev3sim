from queue import Empty
import sys
from unittest import mock
from ev3sim.simulation.loader import runFromConfig
from ev3sim.simulation.randomisation import Randomiser
from luddite import get_version_pypi
from ev3sim.visual.manager import ScreenObjectManager
import yaml
import time
from ev3sim.file_helper import find_abs
from multiprocessing import Process, Queue

def simulate(batch_file, preset_filename, bot_paths, seed, override_settings, *queues):
    result_queue = queues[0]
    send_queues = queues[1::2]
    recv_queues = queues[2::2]
    try:
        ScreenObjectManager.BATCH_FILE = batch_file
        ScreenObjectManager.PRESET_FILE = preset_filename

        import ev3sim

        try:
            latest_version = get_version_pypi("ev3sim")
            ScreenObjectManager.NEW_VERSION = latest_version != ev3sim.__version__
            if ScreenObjectManager.NEW_VERSION:
                update_message = f"""\

    ==========================================================================================
    There is a new version of ev3sim available ({latest_version}).
    Keeping an up to date version of ev3sim ensures you have the latest bugfixes and features.
    Please update ev3sim by running the following command:
        python -m pip install -U ev3sim
    ==========================================================================================

    """
                print(update_message)
        except:
            ScreenObjectManager.NEW_VERSION = False

        Randomiser.createGlobalRandomiserWithSeed(seed)

        preset_file = find_abs(preset_filename, allowed_areas=["local", "local/presets/", "package", "package/presets/"])
        with open(preset_file, "r") as f:
            config = yaml.safe_load(f)

        config["robots"] = config.get("robots", []) + bot_paths

        def run():
            runFromConfig(config, send_queues, recv_queues)

        # Handle any other settings modified by the preset.
        settings = config.get("settings", {})
        settings.update(override_settings)
        for keyword, value in settings.items():
            run = mock.patch(keyword, value)(run)

        run()
    except Exception as e:
        import traceback
        result_queue.put(("Simulation", traceback.format_exc()))
        return
    result_queue.put(True)

def batched_run(batch_file, bind_addr, seed):

    batch_path = find_abs(
        batch_file, allowed_areas=["local", "local/batched_commands/", "package", "package/batched_commands/"]
    )
    with open(batch_path, "r") as f:
        config = yaml.safe_load(f)

    bot_paths = [x["name"] for x in config["bots"]]
    sim_args = [batch_file, config["preset_file"], bot_paths, seed, config.get("settings", {})]
    queues = [Queue() for _ in range(2*len(bot_paths) + 1)]
    sim_args.extend(queues)
    result_queue = queues[0]

    sim_process = Process(
        target=simulate,
        args=sim_args,
    )

    from ev3sim.attach_bot import attach_bot

    bot_processes = []
    for i, bot in enumerate(config["bots"]):
        for script in bot.get("scripts", []):
            fname = find_abs(script, allowed_areas=["local", "local/robots/", "package", "package/robots/"])
            bot_processes.append(Process(
                target=attach_bot,
                args=(f"Robot-{i}", fname, result_queue, queues[2*i+1], queues[2*i+2])
            ))

    sim_process.start()
    for p in bot_processes:
        p.start()

    try:
        while True:
            try:
                r = result_queue.get_nowait()
                break
            except Empty:
                time.sleep(0.05)
    except KeyboardInterrupt:
        r = True
        pass
    sim_process.terminate()
    for p in bot_processes:
        p.terminate()
    if r is not True:
        print(f"An error occurred in the {r[0]} process. Printing the error now...")
        print(r[1])
