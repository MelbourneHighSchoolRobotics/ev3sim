from simulation.interactor import IInteractor
from simulation.world import World
from objects.base import objectFactory
from visual.objects import visualFactory
from visual import ScreenObjectManager

class SpawnerInteractor(IInteractor):

    def __init__(self, **kwargs):
        self.prefix_key = kwargs.get('prefix', 'spawn_')
        self.items = kwargs['elements']
        # Handle any programmatic color references.
        for x in range(len(self.items)):
            if 'fill' in self.items[x] and self.items[x]['fill'] in kwargs:
                self.items[x]['fill'] = kwargs[self.items[x]['fill']]
            if self.items[x]['type'] == 'object' and self.items[x].get('visual', {}).get('fill', '') in kwargs:
                self.items[x]['visual']['fill'] = kwargs[self.items[x]['visual']['fill']]
        self.object_map = {}

    def startUp(self, **kwargs):
        self.objects = []
        for item in self.items:
            if item['type'] == 'visual':
                vis = visualFactory(**item)
                ScreenObjectManager.instance.registerVisual(vis, self.prefix_key + item.get('key', 'object'))
                self.object_map[item.get('key', 'object')] = vis
            elif item['type'] == 'object':
                obj = objectFactory(**item)
                if item.get('physics', False):
                    World.instance.registerObject(obj)    
                ScreenObjectManager.instance.registerObject(obj, self.prefix_key + item.get('key', 'object'))
                self.object_map[item.get('key', 'object')] = obj

    def tick(self, tick):
        return False
