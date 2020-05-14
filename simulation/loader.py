import time
from typing import List
from simulation.interactor import IInteractor
from visual import ScreenObjectManager

class ScriptLoader:

    active_scripts: List[IInteractor]
    VISUAL_TICK_RATE = 30

    def startUp(self, **kwargs):
        man = ScreenObjectManager(**kwargs)
        man.start_screen()

    def simulate(self, *interactors):
        self.active_scripts = list(interactors)
        for interactor in self.active_scripts:
            interactor.startUp()
        tick = 0
        last_vis_update = time.time() - 2 / self.VISUAL_TICK_RATE
        while self.active_scripts:
            to_remove = []
            for i, interactor in enumerate(self.active_scripts):
                if interactor.tick(tick):
                    to_remove.append(i)
            for i in to_remove[::-1]:
                self.active_scripts[i].tearDown()
                del self.active_scripts[i]
            tick += 1
            new_tick = time.time()
            if new_tick - last_vis_update > 1 / self.VISUAL_TICK_RATE:
                last_vis_update = new_tick
                ScreenObjectManager.instance.applyToScreen()
                ScreenObjectManager.instance.checkForClose()
