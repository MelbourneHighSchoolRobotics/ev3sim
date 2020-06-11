import numpy as np

from simulation.interactor import IInteractor
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

    def __init__(self, **kwargs):
        self.options = self.DEFAULT_ROBOT_DEFINITION
        self.options.update(kwargs)

    def startUp(self, **kwargs):
        self.robot = objectFactory(**self.options)
        ScreenObjectManager.instance.registerObject(self.robot, 'testingRobot')

    def tick(self, tick):
        x = tick / 30
        self.robot.rotation = x
        self.robot.position = (
            np.cos(0.3*x) * 30,
            np.sin(0.3*x) * 30,
            1
        )
        return x >= 4 * np.pi / 0.3
