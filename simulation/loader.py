import time
from typing import List
from simulation.interactor import IInteractor
from visual import ScreenObjectManager

class ScriptLoader:

    KEY_TICKS_PER_SECOND = 'tps'

    active_scripts: List[IInteractor]
    VISUAL_TICK_RATE = 30
    GAME_TICK_RATE = 60

    def startUp(self, **kwargs):
        man = ScreenObjectManager(**kwargs)
        man.startScreen()

    def simulate(self, *interactors):
        self.active_scripts = list(interactors)
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
                tick += 1
            if new_time - last_vis_update > 1 / self.VISUAL_TICK_RATE:
                last_vis_update = new_time
                ScreenObjectManager.instance.applyToScreen()
                ScreenObjectManager.instance.checkForClose()

    def getSimulationConstants(self):
        return {
            ScriptLoader.KEY_TICKS_PER_SECOND: self.GAME_TICK_RATE
        }
