import argparse
import sys
from collections import deque
from queue import Queue
import time
from ev3sim.file_helper import find_abs
import yaml
from ev3sim.simulation.loader import runFromConfig, ScriptLoader
from ev3sim.simulation.randomisation import Randomiser
from ev3sim.visual.manager import ScreenObjectManager
from unittest import mock
from luddite import get_version_pypi


def single_run(preset_filename, robots, bind_addr, seed, batch_file=None, override_settings={}):
    if batch_file:
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

    config["robots"] = config.get("robots", []) + robots

    shared_data = {
        "tick": 0,  # Current tick.
        "write_stack": deque(),  # All write actions are processed through this.
        "data_queue": {},  # Simulation data for each bot.
        "active_count": {},  # Keeps track of which code connection each bot has.
        "bot_locks": {},  # Threading Locks and Conditions for each bot to wait for connection actions.
        "bot_communications_data": {},  # Buffers and information for all bot communications.
        "tick_updates": {},  # Simply a dictionary where the simulation tick will push static data, so the other methods are aware of when the simulation has exited.
        "events": {},  # Any events that should be sent to robots.
    }

    result_bucket = Queue(maxsize=1)

    from threading import Thread
    from ev3sim.simulation.communication import start_server_with_shared_data

    def run(shared_data, result):
        try:
            runFromConfig(config, shared_data)
        except Exception as e:
            result.put(("Simulation", e))
            return
        result.put(True)

    # Handle any other settings modified by the preset.
    settings = config.get("settings", {})
    settings.update(override_settings)
    for keyword, value in settings.items():
        run = mock.patch(keyword, value)(run)

    comm_thread = Thread(
        target=start_server_with_shared_data, args=(shared_data, result_bucket, bind_addr), daemon=True
    )
    sim_thread = Thread(target=run, args=(shared_data, result_bucket), daemon=True)

    comm_thread.start()
    sim_thread.start()

    try:
        with result_bucket.not_empty:
            while not result_bucket._qsize():
                result_bucket.not_empty.wait(0.1)
        r = result_bucket.get()
        # Chuck it back on the queue so that other threads know we are quitting.
        result_bucket.put(r)
        if r is not True:
            print(f"An error occurred in the {r[0]} thread. Raising an error now...")
            time.sleep(1)
            raise r[1]
    except KeyboardInterrupt:
        pass
