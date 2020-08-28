def batched_run(batch_file):
    import sys
    import yaml
    from subprocess import Popen, PIPE, TimeoutExpired
    from ev3sim.file_helper import find_abs


    batch_path = find_abs(batch_file, allowed_areas=['local', 'local/batched_commands/', 'package', 'package/batched_commands/'])
    with open(batch_path, 'r') as f:
        config = yaml.safe_load(f)

    bot_paths = [x['name'] for x in config['bots']]
    sim_args = ['ev3sim', '--preset', config['preset_file']]
    sim_args.extend(bot_paths)

    sim_popen = Popen(sim_args, stdout=PIPE)
    script_popens = []
    for i, bot in enumerate(config['bots']):
        for script in bot.get('scripts', []):
            attach_args = ['ev3attach', script, f"Robot-{i}"]
            script_popens.append(Popen(attach_args, stdout=PIPE))

    class NoProblemError(Exception): pass

    try:
        while True:
            try:
                sim_popen.wait(timeout=0.1)
                raise NoProblemError
            except TimeoutExpired:
                pass
            for popen in script_popens:
                try:
                    popen.wait(timeout=0.1)
                    raise NoProblemError
                except TimeoutExpired:
                    pass
    except KeyboardInterrupt:
        pass
    except NoProblemError:
        pass
    sim_popen.kill()
    for popen in script_popens:
        popen.kill()



