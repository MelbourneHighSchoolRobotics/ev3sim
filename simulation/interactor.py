from simulation.world import World
from objects.base import objectFactory
from visual.objects import visualFactory
from visual import ScreenObjectManager

class IInteractor:

    constants: dict

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

    def startUp(self):
        self.objects = []
        for item in self.items:
            if item['type'] == 'visual':
                vis = visualFactory(**item)
                vis.key = self.prefix_key + item.get('key', 'object')
                ScreenObjectManager.instance.registerVisual(vis, vis.key)
                self.object_map[item.get('key', 'object')] = vis
            elif item['type'] == 'object':
                obj = objectFactory(**item)
                obj.key = self.prefix_key + item.get('key', 'object')
                if item.get('physics', False):
                    World.instance.registerObject(obj)    
                ScreenObjectManager.instance.registerObject(obj, obj.key)
                self.object_map[item.get('key', 'object')] = obj

    # tick returns a boolean, which is true if the script should end.
    def tick(self, tick) -> bool:
        return False

    def tearDown(self):
        pass

    # Handles events pumped from pygame.
    def handleEvent(self, event):
        pass

def fromOptions(options):
    if 'filename' in options:
        import yaml
        with open(options['filename'], 'r') as f:
            config = yaml.safe_load(f)
            return fromOptions(config)
    if 'class_path' not in options:
        raise ValueError("Your options has no 'class_path' or 'filename' entry (Or the file you reference has no 'class_path' entry')")
    mname, cname = options['class_path'].rsplit('.', 1)
    import importlib
    klass = getattr(importlib.import_module(mname), cname)
    return klass(*options.get('args', []), **options.get('kwargs', {}))
