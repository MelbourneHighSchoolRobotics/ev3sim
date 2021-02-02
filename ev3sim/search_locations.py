preset_locations = lambda: ["workspace/presets/", "workspace", "package/presets/"]
bot_locations = lambda: ["workspace/robots/", "workspace", "package/examples/robots/"]
code_locations = lambda: ["workspace/code/", "workspace", "package/examples/robots/"]
config_locations = lambda: ["workspace", "package"]
device_locations = lambda: ["workspace/devices/", "package/devices/"]
theme_locations = lambda: ["workspace/assets/", "workspace", "package/assets"]
asset_locations = lambda: ["workspace/assets/", "workspace", "package/assets/"]


def batch_locations():
    """Batch files can also be in the custom folders."""
    import os
    from ev3sim.file_helper import find_abs_directory
    from ev3sim.simulation.loader import StateHandler

    locations = ["workspace/sims/", "workspace", "package/examples/sims/"]
    if StateHandler.WORKSPACE_FOLDER:
        custom_path = find_abs_directory("workspace/custom/", create=True)
        for name in os.listdir(custom_path):
            if os.path.isdir(os.path.join(custom_path, name)):
                locations.append(f"workspace/custom/{name}/")
    return locations
