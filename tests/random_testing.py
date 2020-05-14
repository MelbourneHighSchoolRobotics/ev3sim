import numpy as np

from simulation.interactor import IInteractor
from objects.base import objectFactory
from visual import ScreenObjectManager

class RandomInteractor(IInteractor):

    ROBOT_DEFINITION = {
        'visual': {
            'name': 'Circle',
            'radius': 0.15,
            'fill': '#ff00ff',
            'stroke': '#aaaaaa',
            'stroke_width': 0.01,
        },
        'children': [
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 0.05,
                    'height': 0.1,
                    'fill': '#00ff00',
                    'stroke': '#0000ff',
                    'stroke_width': 0.003,
                },
                'position': (0.125, 0, 1)
            },
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 0.05,
                    'height': 0.1,
                    'stroke': '#ff0000',
                    'stroke_width': 0.003,
                },
                'position': (-0.125, 0, 1)
            },
        ]
    }

    def startUp(self):
        self.robot = objectFactory(**self.ROBOT_DEFINITION)
        ScreenObjectManager.instance.registerObject(self.robot, 'testingRobot')

    def tick(self, tick):
        x = tick / 2000
        self.robot.rotation = x
        self.robot.position = (
            0.5 + np.cos(0.3*x) / 4,
            0.5 + np.sin(0.3*x) / 4,
            1
        )
        return x >= 4 * np.pi / 0.3
