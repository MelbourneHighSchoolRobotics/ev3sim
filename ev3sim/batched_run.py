import sys
import yaml
import time
from ev3sim.file_helper import find_abs
from multiprocessing import Process


def batched_run(batch_file, bind_addr, *args):
    from ev3sim.single_run import single_run as sim
    from ev3sim.attach import main as attach

    batch_path = find_abs(
        batch_file, allowed_areas=["local", "local/batched_commands/", "package", "package/batched_commands/"]
    )
    with open(batch_path, "r") as f:
        config = yaml.safe_load(f)

    bot_paths = [x["name"] for x in config["bots"]]
    sim_args = [config["preset_file"], bot_paths, bind_addr]
    sim_args.extend(args)
    sim_process = Process(
        target=sim,
        args=sim_args,
        kwargs={"batch_file": batch_file, "override_settings": config.get("settings", {})},
    )

    script_processes = []
    for i, bot in enumerate(config["bots"]):
        for script in bot.get("scripts", []):
            script_processes.append(
                Process(
                    target=attach,
                    kwargs={
                        "passed_args": ["Useless", "--send_logs", "--simulator_addr", bind_addr, script, f"Robot-{i}"]
                    },
                )
            )

    sim_process.start()
    time.sleep(0.5)  # Give the gRPC server 500ms to start
    for p in script_processes:
        p.start()

    # At the moment, just wait for the simulator to finish then kill all attach processes.
    # If any attach threads error out, then the stack trace is printed anyways so this is fine.
    sim_process.join()
    for p in script_processes:
        p.terminate()
