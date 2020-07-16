import yaml
import numpy as np
from simulation.interactor import IInteractor, fromOptions
from simulation.loader import ScriptLoader
from objects.base import objectFactory
from objects.utils import local_space_to_world_space
from visual.manager import ScreenObjectManager

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_class = kwargs.get('device')
        self.physical_object = kwargs.get('parent')
        self.relative_location = kwargs.get('relative_location')
        self.relative_rotation = kwargs.get('relative_rotation')
        self.prefix_key = self.physical_object.key + str(self.device_class.__class__)
    
    def startUp(self):
        for i, item in enumerate(self.items):
            obj = objectFactory(**item)
            if hasattr(obj, 'visual') and hasattr(self.physical_object, 'visual'):
                obj.visual.zPos += self.physical_object.visual.zPos
            obj.key = self.prefix_key + item.get('key', 'object') + '_' + str(i)
            if item.get('physics', False):
                World.instance.registerObject(obj)    
            ScreenObjectManager.instance.registerObject(obj, obj.key)
            self.object_map[item.get('key', 'object')] = obj
            self.physical_object.children.append(obj)
    
    def afterPhysics(self):
        for obj in self.object_map.values():
            obj.position = local_space_to_world_space(self.relative_location, self.physical_object.rotation, self.physical_object.position)
            obj.rotation = self.physical_object.rotation + self.relative_rotation

def initialise_device(deviceData, parentObj):
    devices = yaml.safe_load(open('devices/classes.yaml', 'r'))
    name = deviceData['name']
    if name not in devices:
        raise ValueError(f"Unknown device type {name}")
    with open('devices/'+devices[name], 'r') as f:
        try:
            config = yaml.safe_load(f)
            mname, cname = config['class'].rsplit('.', 1)
            import importlib
            klass = getattr(importlib.import_module(mname), cname)
            relative_location = deviceData.get('position', [0, 0])
            relative_rotation = deviceData.get('rotation', 0) * np.pi/180
            device = klass(parentObj, relative_location, relative_rotation)
            for opt in config.get('interactors', []):
                res = opt.get('kwargs', {})
                res.update({
                    'device': device,
                    'parent': parentObj,
                    'relative_location': relative_location,
                    'relative_rotation': relative_rotation
                })
                opt['kwargs'] = res
                ScriptLoader.instance.active_scripts.append(fromOptions(opt))
                # ScriptLoader.instance.active_scripts[-1].startUp()
        except yaml.YAMLError as exc:
            print(f"An error occured while loading devices. Exited with error: {exc}")
        