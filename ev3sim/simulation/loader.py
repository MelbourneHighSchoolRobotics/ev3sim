from queue import Empty
import time
from typing import List
from ev3sim.objects.base import objectFactory
from ev3sim.simulation.bot_comms import BotCommService
from ev3sim.simulation.interactor import IInteractor, fromOptions
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.visual import ScreenObjectManager
from ev3sim.visual.objects import visualFactory
import ev3sim.visual.utils
from ev3sim.constants import *


class ScriptLoader:

    SEND = 0
    RECV = 1

    KEY_TICKS_PER_SECOND = "tps"

    active_scripts: List[IInteractor]
    VISUAL_TICK_RATE = 30
    GAME_TICK_RATE = 30
    TIME_SCALE = 1
    # TIME_SCALE simply affects the speed at which the simulation runs
    # (TIME_SCALE = 2, GAME_TICK_RATE = 30 implies 60 ticks of per actual seconds)

    RANDOMISE_SENSORS = False

    instance: "ScriptLoader" = None
    running = True

    def __init__(self, **kwargs):
        ScriptLoader.instance = self
        self.robots = {}
        self.queues = {}
        self.outstanding_events = {}
        self.comms = BotCommService()

    def addActiveScript(self, script: IInteractor):
        idx = len(self.active_scripts)
        for x in range(len(self.active_scripts)):
            if self.active_scripts[x].SORT_ORDER > script.SORT_ORDER:
                idx = x
                break
        self.active_scripts.insert(idx, script)

    def sendEvent(self, botID, eventName, eventData):
        self.outstanding_events[botID].append((eventName, eventData))

    def setRobotQueues(self, botID, sendQ, recvQ):
        self.queues[botID] = (sendQ, recvQ)

    def startUp(self, **kwargs):
        man = ScreenObjectManager(**kwargs)
        man.startScreen()
        self.world = World()
        self.object_map = {}

    def loadElements(self, items):
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
                    initialise_device(device, obj, index)
                if item.get("physics", False):
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

    def simulate(self):
        for interactor in self.active_scripts:
            interactor.constants = self.getSimulationConstants()
            interactor.startUp()
        self.physics_tick = 0
        tick = 0
        last_vis_update = time.time() - 1.1 / self.VISUAL_TICK_RATE
        last_game_update = time.time() - 1.1 / self.GAME_TICK_RATE / self.TIME_SCALE
        total_lag_ticks = 0
        lag_printed = False
        while self.active_scripts:
            if not self.running:
                return
            new_time = time.time()
            if new_time - last_game_update > 1 / self.GAME_TICK_RATE / self.TIME_SCALE:
                self.handleWrites()
                self.setValues()
                # Handle simulation.
                # First of all, check the script can handle the current settings.
                if new_time - last_game_update > 2 / self.GAME_TICK_RATE / self.TIME_SCALE:
                    total_lag_ticks += 1
                last_game_update = new_time
                to_remove = []
                for i, interactor in enumerate(self.active_scripts):
                    if interactor.tick(tick):
                        to_remove.append(i)
                for i in to_remove[::-1]:
                    self.active_scripts[i].tearDown()
                    del self.active_scripts[i]
                self.world.tick(1 / self.GAME_TICK_RATE)
                for interactor in self.active_scripts:
                    interactor.afterPhysics()
                tick += 1
                self.incrementPhysicsTick()
                if (tick > 10 and total_lag_ticks / tick > 0.5) and not lag_printed:
                    lag_printed = True
                    print("The simulation is currently lagging, you may want to turn down the game tick rate.")
            if new_time - last_vis_update > 1 / self.VISUAL_TICK_RATE:
                last_vis_update = new_time
                ScreenObjectManager.instance.applyToScreen()
                for event in ScreenObjectManager.instance.handleEvents():
                    for interactor in self.active_scripts:
                        interactor.handleEvent(event)

    def getSimulationConstants(self):
        return {ScriptLoader.KEY_TICKS_PER_SECOND: self.GAME_TICK_RATE}


def runFromConfig(config, send_queues, recv_queues):
    from collections import defaultdict
    from ev3sim.robot import initialise_bot, RobotInteractor
    from ev3sim.file_helper import find_abs

    sl = ScriptLoader()
    sl.active_scripts = []
    ev3sim.visual.utils.GLOBAL_COLOURS = config.get("colours", {})
    # Keep track of index w.r.t. filename.
    robot_paths = defaultdict(lambda: 0)
    for index, robot in enumerate(config.get("robots", [])):
        robot_path = find_abs(robot, allowed_areas=["local", "local/robots/", "package", "package/robots/"])
        initialise_bot(config, robot_path, f"Robot-{index}", robot_paths[robot_path])
        robot_paths[robot_path] += 1
        sl.setRobotQueues(f"Robot-{index}", send_queues[index], recv_queues[index])
    for opt in config.get("interactors", []):
        try:
            sl.addActiveScript(fromOptions(opt))
        except Exception as exc:
            print(f"Failed to load interactor with the following options: {opt}. Got error: {exc}")
    if sl.active_scripts:
        sl.startUp()
        sl.loadElements(config.get("elements", []))
        for interactor in sl.active_scripts:
            if isinstance(interactor, RobotInteractor):
                interactor.connectDevices()
        sl.simulate()
    else:
        print("No interactors successfully loaded. Quitting...")
