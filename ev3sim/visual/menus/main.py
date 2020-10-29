import pygame_menu

def on_button_simulate(*args, **kwargs):
    from ev3sim.visual.manager import ScreenObjectManager
    ScreenObjectManager.instance.pushScreen(ScreenObjectManager.instance.SCREEN_BATCH)

class MainMenu(pygame_menu.Menu):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_button("Click me", on_button_simulate, "test", clear=True)

    def initWithKwargs(self, **kwargs):
        pass

    def onPop(self):
        pass
