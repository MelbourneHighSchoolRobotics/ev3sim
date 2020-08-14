import time
from typing import List
from ev3sim.objects.base import objectFactory
from ev3sim.simulation.interactor import IInteractor, fromOptions
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.visual import ScreenObjectManager
from ev3sim.visual.objects import visualFactory
import ev3sim.visual.utils

class ScriptLoader:

    KEY_TICKS_PER_SECOND = 'tps'

    active_scripts: List[IInteractor]
    VISUAL_TICK_RATE = 30
    GAME_TICK_RATE = 60
    TIME_SCALE = 1
    # TIME_SCALE simply affects the speed at which the simulation runs 
    # (TIME_SCALE = 2, GAME_TICK_RATE = 30 implies 60 ticks of per actual seconds)

    instance: 'ScriptLoader' = None
    running = True

    def __init__(self, **kwargs):
        ScriptLoader.instance = self
        self.robots = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    def setSharedData(self, data):
        self.data = data

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
            assert 'key' in item and 'type' in item, f"Each item requires a key and type. {item}"
            if item['type'] == 'visual':
                vis = visualFactory(**item)
                vis.key = item["key"]
                ScreenObjectManager.instance.registerVisual(vis, vis.key)
                self.object_map[item["key"]] = vis
                elements.append(vis)
            elif item['type'] == 'object':
                devices = []
                to_remove = []
                for x in range(len(item.get('children', []))):
                    if item['children'][x]['type'] == 'device':
                        devices.append(item['children'][x])
                        to_remove.append(x)
                for x in to_remove[::-1]:
                    del item['children'][x]
                obj = objectFactory(**item)
                obj.key = item["key"]
                for index, device in enumerate(devices):
                    # Instantiate the devices.
                    initialise_device(device, obj, index)
                if item.get('physics', False):
                    World.instance.registerObject(obj)    
                ScreenObjectManager.instance.registerObject(obj, obj.key)
                self.object_map[obj.key] = obj
                elements.append(obj)
        return elements

    @stop_on_pause
    def incrementPhysicsTick(self):
        self.physics_tick += 1
        self.data['tick'] = self.physics_tick

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
                # Handle any writes
                while self.data['write_stack']:
                    rob_id, attribute_path, value = self.data['write_stack'].popleft()
                    sensor_type, specific_sensor, attribute = attribute_path.split()
                    self.robots[rob_id].getDeviceFromPath(sensor_type, specific_sensor).applyWrite(attribute, value)
                for key, robot in self.robots.items():
                    if key in self.data['data_queue']:
                        self.data['data_queue'][key].put(robot._interactor.collectDeviceData())
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
        return {
            ScriptLoader.KEY_TICKS_PER_SECOND: self.GAME_TICK_RATE
        }

def runFromConfig(config, shared):
    from ev3sim.robot import initialise_bot, RobotInteractor
    from ev3sim.file_helper import find_abs
    sl = ScriptLoader(**config.get('loader', {}))
    sl.setSharedData(shared)
    sl.active_scripts = []
    ev3sim.visual.utils.GLOBAL_COLOURS = config.get('colours', {})
    for index, robot in enumerate(config.get('robots', [])):
        robot_path = find_abs(robot, allowed_areas=['local', 'local/robots/', 'package', 'package/robots/'])
        initialise_bot(config, robot_path, f'Robot-{index}')
    for opt in config.get('interactors', []):
        try:
            sl.active_scripts.append(fromOptions(opt))
        except Exception as exc:
            print(f"Failed to load interactor with the following options: {opt}. Got error: {exc}")
    if sl.active_scripts:
        sl.startUp(**config.get('screen', {}))
        sl.loadElements(config.get('elements', []))
        for interactor in sl.active_scripts:
            if isinstance(interactor, RobotInteractor):
                interactor.connectDevices()
        sl.simulate()
    else:
        print("No interactors succesfully loaded. Quitting...")
