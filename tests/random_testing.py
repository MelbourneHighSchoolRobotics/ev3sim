import numpy as np

from simulation.interactor import IInteractor
from visual import ScreenObjectManager, Rectangle, Circle

class RandomInteractor(IInteractor):

    def startUp(self):
        self.rect = Rectangle(height=0.15, width=0.3, stroke='#ff0000')
        self.rect2 = Rectangle(height=0.15, width=0.3, fill='#00ff00', stroke='#0000ff')
        self.circle = Circle(radius=0.15, fill='#ff00ff', stroke='#aaaaaa', stroke_width=0.01)
        ScreenObjectManager.instance.registerObject(self.rect, 'testingRect')
        ScreenObjectManager.instance.registerObject(self.rect2, 'testingRect2')
        ScreenObjectManager.instance.registerObject(self.circle, 'testingCircle')

    def tick(self, tick):
        x = tick / 2000
        self.circle.position = (
            0.5 + np.cos(-0.3*x) / 10,
            0.5 + np.sin(-0.3*x) / 10,
            2
        )
        self.rect.rotation = x
        self.rect.position = (
            0.5 + np.cos(0.3*x) / 4,
            0.5 + np.sin(0.3*x) / 4,
            1
        )
        self.rect2.rotation = x + np.pi / 2
        self.rect2.position = (
            0.5 + np.cos(0.3*x) / 4,
            0.5 + np.sin(0.3*x) / 4,
            0
        )
        return x >= 4 * np.pi / 0.3
