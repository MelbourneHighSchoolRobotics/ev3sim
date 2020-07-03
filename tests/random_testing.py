import numpy as np

from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from simulation.world import World
from objects.base import objectFactory
from visual import ScreenObjectManager

class RandomInteractor(IInteractor):

    DEFAULT_ROBOT_DEFINITION = {
        'visual': {
            'name': 'Circle',
            'radius': 20,
            'fill': '#ff00ff',
            'stroke': '#aaaaaa',
            'stroke_width': 3,
        },
        'children': [
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 10,
                    'height': 20,
                    'fill': '#00ff00',
                    'stroke': '#0000ff',
                    'stroke_width': 2,
                },
                'position': (15, 0, 1)
            },
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 10,
                    'height': 20,
                    'stroke': '#ff0000',
                    'stroke_width': 2,
                },
                'position': (-15, 0, 1)
            },
        ]
    }

    key = 'testingRobot'
    offset = 0

    def __init__(self, **kwargs):
        if 'key' in kwargs:
            self.key = kwargs.pop('key')
        if 'offset' in kwargs:
            self.offset = kwargs.pop('offset')
        self.options = self.DEFAULT_ROBOT_DEFINITION.copy()
        self.options.update(kwargs)

    def startUp(self, **kwargs):
        self.robot = objectFactory(**self.options)
        World.instance.registerObject(self.robot)
        ScreenObjectManager.instance.registerObject(self.robot, self.key)

    def tick(self, tick):
        x = 3 * tick / self.constants[ScriptLoader.KEY_TICKS_PER_SECOND]
        self.robot.rotation = x
        self.robot.position = (
            np.cos(0.3*x + self.offset * 2 * np.pi) * (30-x),
            np.sin(0.3*x + self.offset * 2 * np.pi) * (30-x),
            1
        )
        return x >= 4 * np.pi / 0.3
