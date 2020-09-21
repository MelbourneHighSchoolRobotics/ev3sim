import sys
import yaml
import time
from ev3sim.file_helper import find_abs
from multiprocessing import Process


def batched_run(batch_file, bind_addr):
    from ev3sim.batched import single_run as sim

    batch_path = find_abs(
        batch_file, allowed_areas=["local", "local/batched_commands/", "package", "package/batched_commands/"]
    )
    with open(batch_path, "r") as f:
        config = yaml.safe_load(f)

    bot_paths = [x["name"] for x in config["bots"]]
    sim_process = Process(
        target=sim, args=[config["preset_file"], bot_paths, bind_addr], kwargs={"batch_file": batch_file}
    )

    bot_data = []

    for i, bot in enumerate(config["bots"]):
        if bot.get("scripts", []):
            bot_data.append((bot["scripts"][0], f"Robot-{i}"))

    sim(config["preset_file"], bot_paths, bind_addr, batch_file, bot_data)
