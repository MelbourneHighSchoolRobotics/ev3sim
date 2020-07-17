import time
from typing import List
from objects.base import objectFactory
from simulation.interactor import IInteractor, fromOptions
from simulation.world import World
from visual import ScreenObjectManager
from visual.objects import visualFactory
import visual.utils

class ScriptLoader:

    KEY_TICKS_PER_SECOND = 'tps'

    active_scripts: List[IInteractor]
    VISUAL_TICK_RATE = 30
    GAME_TICK_RATE = 60

    instance: 'ScriptLoader' = None

    def __init__(self, **kwargs):
        ScriptLoader.instance = self
        for key, value in kwargs.items():
            setattr(self, key, value)

    def startUp(self, **kwargs):
        man = ScreenObjectManager(**kwargs)
        man.startScreen()
        self.world = World()
        self.object_map = {}

    def loadElements(self, items):
        # Handle any programmatic color references.
        elements = []
        from devices.base import initialise_device
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

    def simulate(self, *interactors):
        self.active_scripts.extend(interactors)
        for interactor in self.active_scripts:
            interactor.constants = self.getSimulationConstants()
            interactor.startUp()
        tick = 0
        last_vis_update = time.time() - 2 / self.VISUAL_TICK_RATE
        last_game_update = time.time() - 2 / self.GAME_TICK_RATE
        while self.active_scripts:
            new_time = time.time()
            if new_time - last_game_update > 1 / self.GAME_TICK_RATE:
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


def runFromFile(filename):
    import yaml
    with open(filename, 'r') as f:
        try:
            config = yaml.safe_load(f)
            sl = ScriptLoader(**config.get('loader', {}))
            sl.active_scripts = []
            visual.utils.GLOBAL_COLOURS = config.get('colours', {})
            interactors = []
            for opt in config.get('interactors', []):
                try:
                    interactors.append(fromOptions(opt))
                except Exception as exc:
                    print(f"Failed to load interactor with the following options: {opt}. Got error: {exc}")
            if interactors:
                sl.startUp(**config.get('screen', {}))
                sl.loadElements(config.get('elements', []))
                sl.simulate(*interactors)
            else:
                print("No interactors succesfully loaded. Quitting...")
        except yaml.YAMLError as exc:
            print(f"An error occured while loading script preset {filename}. Exited with error: {exc}")
