import yaml
import numpy as np
from simulation.interactor import IInteractor, fromOptions
from simulation.loader import ScriptLoader
from objects.base import objectFactory
from objects.utils import local_space_to_world_space
from visual.manager import ScreenObjectManager
import visual.utils as utils

class Device:

    def __init__(self, parent, relativePos, relativeRot):
        # parent is the physics object containing this device.
        # visual is the object representing the device
        self.parent = parent
        self.relativePos = relativePos
        self.relativeRot = relativeRot
    
    @property
    def global_position(self):
        return self.parent.position + np.array([
            self.relativePos[0] * np.cos(self.parent.rotation) - self.relativePos[1] * np.sin(self.parent.rotation),
            self.relativePos[1] * np.cos(self.parent.rotation) + self.relativePos[0] * np.sin(self.parent.rotation)
        ])

class IDeviceInteractor(IInteractor):

    name = 'UNNAMED'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_class = kwargs.get('device')
        self.physical_object = kwargs.get('parent')
        self.relative_location = kwargs.get('relative_location')
        self.relative_rotation = kwargs.get('relative_rotation')
        i1, i2 = kwargs.get('device_index'), kwargs.get('single_device_index')
        self.index = f'{i1}-{i2}'
        self.prefix_key = self.physical_object.key + str(self.device_class.__class__)
        self.items = kwargs.get('elements', [])
    
    def getPrefix(self):
        return f'{self.name}-{self.index}-'

    def startUp(self):
        for x in range(len(self.items)):
            self.items[x]["key"] = self.getPrefix() + self.items[x]["key"]
            self.items[x]["type"] = 'object'
        self.generated = ScriptLoader.instance.loadElements(self.items)
        self.physical_object.children.extend(self.generated)
        for obj in self.physical_object.children:
            if hasattr(obj, 'visual') and hasattr(self.physical_object, 'visual'):
                obj.visual.zPos += self.physical_object.visual.zPos
    
    def afterPhysics(self):
        for obj in self.generated:
            obj.position = local_space_to_world_space(self.relative_location, self.physical_object.rotation, self.physical_object.position)
            obj.rotation = self.physical_object.rotation + self.relative_rotation

def initialise_device(deviceData, parentObj, index):
    devices = yaml.safe_load(open('devices/classes.yaml', 'r'))
    name = deviceData['name']
    if name not in devices:
        raise ValueError(f"Unknown device type {name}")
    with open('devices/'+devices[name], 'r') as f:
        try:
            config = yaml.safe_load(f)
            utils.GLOBAL_COLOURS.update(config.get('colours', {}))
            mname, cname = config['class'].rsplit('.', 1)
            import importlib
            klass = getattr(importlib.import_module(mname), cname)
            relative_location = deviceData.get('position', [0, 0])
            relative_rotation = deviceData.get('rotation', 0) * np.pi/180
            device = klass(parentObj, relative_location, relative_rotation)
            for i, opt in enumerate(config.get('interactors', [])):
                res = opt.get('kwargs', {})
                res.update({
                    'device': device,
                    'parent': parentObj,
                    'relative_location': relative_location,
                    'relative_rotation': relative_rotation,
                    'device_index': index,
                    'single_device_index': i,
                })
                opt['kwargs'] = res
                ScriptLoader.instance.active_scripts.append(fromOptions(opt))
        except yaml.YAMLError as exc:
            print(f"An error occured while loading devices. Exited with error: {exc}")
        