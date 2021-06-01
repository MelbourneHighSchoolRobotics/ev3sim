import time
from ev3sim.logging import Logger
from ev3sim.settings import ObjectSetting, SettingsManager
from queue import Empty
from multiprocessing import Process
from typing import List

from ev3sim.objects.base import objectFactory
from ev3sim.simulation.bot_comms import BotCommService
from ev3sim.simulation.interactor import IInteractor, fromOptions
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.visual.manager import ScreenObjectManager, screen_settings
from ev3sim.visual.objects import visualFactory
import ev3sim.visual.utils
from ev3sim.constants import *
from ev3sim.search_locations import bot_locations
from ev3sim.file_helper import ensure_workspace_filled, find_abs, find_abs_directory, WorkspaceError


class ScriptLoader:

    SEND = 0
    RECV = 1

    active_scripts: List[IInteractor]

    # TIME_SCALE simply affects the speed at which the simulation runs
    # (TIME_SCALE = 2, GAME_TICK_RATE = 30 implies 60 ticks of per actual seconds)
    GAME_TICK_RATE = 30
    VISUAL_TICK_RATE = 30
    TIME_SCALE = 1

    RANDOMISE_SENSORS = False

    instance: "ScriptLoader" = None
    running = True

    def __init__(self, **kwargs):
        ScriptLoader.instance = self
        self.robots = {}
        self.queues = {}
        self.processes = {}
        self.scriptnames = {}
        self.outstanding_events = {}
        self.comms = BotCommService()
        self.active_scripts = []
        self.all_scripts = []

    def reset(self):
        for script in self.all_scripts:
            if hasattr(script, "_settings_name"):
                SettingsManager.instance.removeSetting(script._settings_name)
        self.killAllProcesses()
        self.active_scripts = []
        self.all_scripts = []
        self.robots = {}
        self.scriptnames = {}

    def startProcess(self, robot_id, kill_recent=True):
        if robot_id in self.processes and self.processes[robot_id] is not None:
            if kill_recent:
                self.killProcess(robot_id)
            else:
                raise ValueError("Did not expect an existing process!")
        if self.scriptnames[robot_id] is not None:
            from os.path import join, split, dirname
            from ev3sim.attach_bot import attach_bot

            if self.scriptnames[robot_id].endswith(".ev3"):
                actual_script = join(dirname(self.scriptnames[robot_id]), ".compiled.py")
                try:
                    from mindpile import from_ev3

                    with open(actual_script, "w") as f:
                        f.write(from_ev3(self.scriptnames[robot_id], ev3sim_support=True))
                except Exception as e:
                    with open(actual_script, "w") as f:
                        f.write(f'print("Mindstorms compilation failed! {e}")')
            else:
                actual_script = self.scriptnames[robot_id]

            format_filename = join(actual_script)
            # This ensures that as long as the code sits in the bot directory, relative imports will work fine.
            possible_locations = ["workspace/robots/", "workspace", "package/examples/robots"]
            extra_dirs = []
            for loc in possible_locations:
                loc_path = find_abs_directory(loc, create=True)
                if format_filename.startswith(loc_path):
                    while format_filename.startswith(loc_path):
                        format_filename, file = split(format_filename)
                        extra_dirs.append(format_filename)
                    break
            else:
                raise ValueError(f"Expected code to be in one of the following locations: {possible_locations}")

            self.processes[robot_id] = Process(
                target=attach_bot,
                args=(
                    robot_id,
                    actual_script,
                    extra_dirs[::-1],
                    StateHandler.instance.shared_info["result_queue"],
                    StateHandler.instance.shared_info["result_queue"]._internal_size,
                    self.queues[robot_id][self.SEND],
                    self.queues[robot_id][self.SEND]._internal_size,
                    self.queues[robot_id][self.RECV],
                    self.queues[robot_id][self.RECV]._internal_size,
                ),
            )
            self.processes[robot_id].start()
            Logger.instance.beginLog(robot_id)

    def killProcess(self, robot_id, allow_empty=True):
        if robot_id in self.processes and self.processes[robot_id] is not None:
            self.processes[robot_id].terminate()
            self.processes[robot_id].join()
            self.processes[robot_id].close()
            self.processes[robot_id] = None
        elif not allow_empty:
            raise ValueError("Expected an existing process!")
        # Clear all the robot queues. Do this regardless of whether the process existed.
        for key in (ScriptLoader.instance.SEND, ScriptLoader.instance.RECV):
            while True:
                try:
                    ScriptLoader.instance.queues[robot_id][key].get_nowait()
                except (Empty, KeyError):
                    break

    def killAllProcesses(self):
        for rob_id in self.robots:
            self.killProcess(rob_id, allow_empty=True)

    def addActiveScript(self, script: IInteractor):
        idx = len(self.active_scripts)
        for x in range(len(self.active_scripts)):
            if self.active_scripts[x].SORT_ORDER > script.SORT_ORDER:
                idx = x
                break
        self.active_scripts.insert(idx, script)
        self.all_scripts.insert(idx, script)

    def sendEvent(self, botID, eventName, eventData):
        self.outstanding_events[botID].append((eventName, eventData))

    def setRobotQueues(self, botID, sendQ, recvQ):
        self.queues[botID] = (sendQ, recvQ)

    def startUp(self):
        self.object_map = {}
        self.physics_tick = 0
        self.current_tick = 0
        self.input_messages = []
        self.input_requests = []

    def loadElements(self, items, preview_mode=False):
        # Handle any programmatic color references.
        elements = []
        from ev3sim.devices.base import initialise_device

        for item in items:
            assert "key" in item and "type" in item, f"Each item requires a key and type. {item}"
            if item["type"] == "visual":
                vis = visualFactory(**item)
                vis.key = item["key"]
                ScreenObjectManager.instance.registerVisual(vis, vis.key)
                self.object_map[item["key"]] = vis
                elements.append(vis)
            elif item["type"] == "object":
                devices = []
                to_remove = []
                for x in range(len(item.get("children", []))):
                    if item["children"][x]["type"] == "device":
                        devices.append(item["children"][x])
                        to_remove.append(x)
                for x in to_remove[::-1]:
                    del item["children"][x]
                obj = objectFactory(**item)
                obj.key = item["key"]
                for index, device in enumerate(devices):
                    # Instantiate the devices.
                    initialise_device(device, obj, index, preview_mode=preview_mode)
                if item.get("physics", False) and not preview_mode:
                    World.instance.registerObject(obj)
                ScreenObjectManager.instance.registerObject(obj, obj.key)
                self.object_map[obj.key] = obj
                elements.append(obj)
        return elements

    @stop_on_pause
    def incrementPhysicsTick(self):
        self.physics_tick += 1

    def handleWrites(self):
        for rob_id in self.robots:
            r_queue = self.queues[rob_id][self.RECV]
            while True:
                try:
                    write_type, data = r_queue.get_nowait()
                    if write_type == DEVICE_WRITE:
                        attribute_path, value = data
                        sensor_type, specific_sensor, attribute = attribute_path.split()
                        self.robots[rob_id].getDeviceFromPath(sensor_type, specific_sensor).applyWrite(attribute, value)
                    elif write_type == START_SERVER:
                        self.comms.startServer(data["connection_string"], data["robot_id"])
                    elif write_type == CLOSE_SERVER:
                        self.comms.closeServer(data["connection_string"], data["robot_id"])
                    elif write_type == JOIN_CLIENT:
                        self.comms.attemptConnectToServer(data["robot_id"], data["connection_string"])
                    elif write_type == CLOSE_CLIENT:
                        self.comms.closeClient(data["connection_string"], data["robot_id"])
                    elif write_type == SEND_DATA:
                        self.comms.handleSend(
                            data["robot_id"], data["send_to"], data["connection_string"], data["data"]
                        )
                    elif write_type == MESSAGE_PRINT:
                        Logger.instance.writeMessage(data["robot_id"], data["data"], **data.get("kwargs", {}))

                        class Event:
                            pass

                        event = Event()
                        event.type = EV3SIM_PRINT
                        event.robot_id = data["robot_id"]
                        event.message = data["data"]
                        ScreenObjectManager.instance.unhandled_events.append(event)
                    elif write_type == MESSAGE_INPUT_REQUESTED:
                        self.requestInput(data["robot_id"], data["message"])
                    elif write_type == BOT_COMMAND:

                        class Event:
                            pass

                        event = Event()
                        event.type = EV3SIM_BOT_COMMAND
                        event.command_type = data["command_type"]
                        event.robot_id = data["robot_id"]
                        event.payload = data["payload"]
                        ScreenObjectManager.instance.unhandled_events.append(event)
                except Empty:
                    break

    # Maximum amount of times simulation will push data without it being handled.
    MAX_DEAD_SENDS = 10

    def setValues(self):
        for key, robot in self.robots.items():
            s_queue = self.queues[key][self.SEND]
            good = True
            if s_queue.qsize() > self.MAX_DEAD_SENDS:
                good = False
            if (not good) or (not robot.spawned):
                continue
            info = {
                "tick": self.physics_tick,
                "tick_rate": self.GAME_TICK_RATE,
                "events": self.outstanding_events[key],
                "data": robot._interactor.collectDeviceData(),
            }
            self.outstanding_events[key] = []
            s_queue.put((SIM_DATA, info))

    def handleEvents(self, events):
        for event in events:
            for interactor in self.active_scripts:
                interactor.handleEvent(event)

    def simulation_tick(self):
        self.handleWrites()
        self.setValues()
        to_remove = []
        for i, interactor in enumerate(self.active_scripts):
            if interactor.tick(self.current_tick):
                to_remove.append(i)
        for i in to_remove[::-1]:
            self.active_scripts[i].tearDown()
            del self.active_scripts[i]
        World.instance.tick(1 / self.GAME_TICK_RATE)
        for interactor in self.active_scripts:
            interactor.afterPhysics()
        self.incrementPhysicsTick()
        self.current_tick += 1

    def consumeMessage(self, message, output):
        if isinstance(output, IInteractor):
            output.handleInput(message)
        else:
            # Assumed to be robot id.
            self.queues[output][self.SEND].put((SIM_INPUT, message))
        # If there is a prompt being shown in console, remove it.
        sim = ScreenObjectManager.instance.screens[ScreenObjectManager.instance.SCREEN_SIM]
        to_remove = []
        for i, message in enumerate(sim.messages):
            if message[1] == f"input_{str(output)}":
                to_remove.append(i)
        for index in to_remove[::-1]:
            del sim.messages[index]
        sim.regenerateObjects()

    def postInput(self, message, preffered_output=None):
        # First, try to grab an existing request from the queue.
        for i, output in enumerate(self.input_requests):
            if preffered_output is None or preffered_output == output:
                del self.input_requests[i]
                self.consumeMessage(message, output)

                class Event:
                    pass

                event = Event()
                event.type = EV3SIM_MESSAGE_POSTED
                event.output = output
                event.message = message
                ScreenObjectManager.instance.unhandled_events.append(event)
                break
        else:
            self.input_messages.append([message, preffered_output])

    def requestInput(self, output, message):
        # First, try to grab an existing message from the queue.
        for i, (msg, out) in enumerate(self.input_messages):
            if out is None or out == output:
                del self.input_messages[i]
                self.consumeMessage(msg, output)
                break
        else:
            self.input_requests.append(output)
            if message is not None:
                preamble = "[System] " if isinstance(output, IInteractor) else f"[{output}] "
                ScreenObjectManager.instance.screens[ScreenObjectManager.instance.SCREEN_SIM].printStyledMessage(
                    preamble + message,
                    alive_id=f"input_{str(output)}",
                    push_to_front=True,
                )
        if len(self.input_requests) > 0:
            ScreenObjectManager.instance.screens[ScreenObjectManager.instance.SCREEN_SIM].regenerateObjects()


class WorkspaceSetting(ObjectSetting):
    def on_change(self, new_value):
        super().on_change(new_value)
        ensure_workspace_filled(new_value)


class StateHandler:
    """
    Handles the current sim state, and passes information to the simulator, or other menus where appropriate.
    """

    instance: "StateHandler" = None

    is_simulating = False
    is_running = True

    shared_info: dict

    WORKSPACE_FOLDER = None
    SEND_CRASH_REPORTS = None

    def __init__(self):
        StateHandler.instance = self
        sl = ScriptLoader()
        world = World()
        logger = Logger()
        settings = SettingsManager()
        loader_settings = {
            "FPS": ObjectSetting(ScriptLoader, "VISUAL_TICK_RATE"),
            "tick_rate": ObjectSetting(ScriptLoader, "GAME_TICK_RATE"),
            "timescale": ObjectSetting(ScriptLoader, "TIME_SCALE"),
            "console_log": ObjectSetting(Logger, "LOG_CONSOLE"),
            "workspace_folder": WorkspaceSetting(StateHandler, "WORKSPACE_FOLDER"),
            "send_crash_reports": ObjectSetting(StateHandler, "SEND_CRASH_REPORTS"),
        }
        settings.addSettingGroup("app", loader_settings)
        settings.addSettingGroup("screen", screen_settings)
        self.shared_info = {}

    def closeProcesses(self):
        ScriptLoader.instance.killAllProcesses()
        # Clear the result queue.
        while True:
            try:
                self.shared_info["result_queue"].get_nowait()
            except Empty:
                break

    def setConfig(self, **kwargs):
        SettingsManager.instance.setMany(kwargs)

    def startUp(self, **kwargs):
        man = ScreenObjectManager()
        man.startScreen(**kwargs)

    def beginSimulation(self, batch, seed=None):
        self.is_simulating = True
        from ev3sim.sim import start_batch

        start_batch(batch, seed=seed)

    def mainLoop(self):
        last_vis_update = time.time() - 1.1 / ScriptLoader.instance.VISUAL_TICK_RATE
        last_game_update = time.time() - 1.1 / ScriptLoader.instance.GAME_TICK_RATE / ScriptLoader.instance.TIME_SCALE
        total_lag_ticks = 0
        lag_printed = False
        while self.is_running:
            try:
                new_time = time.time()
                if self.is_simulating:
                    if (
                        new_time - last_game_update
                        > 1 / ScriptLoader.instance.GAME_TICK_RATE / ScriptLoader.instance.TIME_SCALE
                    ):
                        ScriptLoader.instance.simulation_tick()
                        if (
                            new_time - last_game_update
                            > 2 / ScriptLoader.instance.GAME_TICK_RATE / ScriptLoader.instance.TIME_SCALE
                        ):
                            total_lag_ticks += 1
                        last_game_update = new_time
                        if (
                            ScriptLoader.instance.current_tick > 10
                            and total_lag_ticks / ScriptLoader.instance.current_tick > 0.5
                        ) and not lag_printed:
                            lag_printed = True
                            print("The simulation is currently lagging, you may want to turn down the game tick rate.")
                    try:
                        r = self.shared_info["result_queue"].get_nowait()
                        if r is not True:
                            Logger.instance.reportError(r[0], r[1])
                    except Empty:
                        pass
                if new_time - last_vis_update > 1 / ScriptLoader.instance.VISUAL_TICK_RATE:
                    last_vis_update = new_time
                    events = ScreenObjectManager.instance.handleEvents()
                    if self.is_running:
                        # We might've closed with those events.
                        if self.is_simulating:
                            ScriptLoader.instance.handleEvents(events)
                        ScreenObjectManager.instance.applyToScreen()
            except WorkspaceError:
                pass


def initialiseFromConfig(config, send_queues, recv_queues):
    from collections import defaultdict
    from ev3sim.robot import initialise_bot, RobotInteractor

    ev3sim.visual.utils.GLOBAL_COLOURS = config.get("colours", {})
    # Keep track of index w.r.t. filename.
    robot_paths = defaultdict(lambda: 0)
    for index, robot in enumerate(config.get("robots", [])):
        robot_path = find_abs(robot, allowed_areas=bot_locations())
        initialise_bot(config, robot_path, f"Robot-{index}", robot_paths[robot_path])
        robot_paths[robot_path] += 1
        ScriptLoader.instance.setRobotQueues(f"Robot-{index}", send_queues[index], recv_queues[index])
    for opt in config.get("interactors", []):
        try:
            ScriptLoader.instance.addActiveScript(fromOptions(opt))
        except Exception as exc:
            print(f"Failed to load interactor with the following options: {opt}. Got error: {exc}")
    SettingsManager.instance.setMany(config["settings"])
    if ScriptLoader.instance.active_scripts:
        ScriptLoader.instance.startUp()
        ScriptLoader.instance.loadElements(config.get("elements", []))
        for interactor in ScriptLoader.instance.active_scripts:
            if isinstance(interactor, RobotInteractor):
                interactor.connectDevices()
        for interactor in ScriptLoader.instance.active_scripts:
            interactor.startUp()
    else:
        print("No interactors successfully loaded. Quitting...")
