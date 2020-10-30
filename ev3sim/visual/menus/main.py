import pygame
from pygame import event
import pygame_gui


def on_button_simulate(*args, **kwargs):
    from ev3sim.visual.manager import ScreenObjectManager

    ScreenObjectManager.instance.pushScreen(ScreenObjectManager.instance.SCREEN_BATCH)


class MainMenu(pygame_gui.UIManager):
    def __init__(self, size, *args, **kwargs):
        self._size = size
        super().__init__(size, *args, **kwargs)
        self.button_size = self._size[0] / 4, self._size[1] / 6
        self._all_objs = []

    def initWithKwargs(self, **kwargs):
        for obj in self._all_objs:
            obj.kill()
        self._all_objs = []
        # In order to respect theme changes, objects must be built in initWithKwargs
        self.bg = pygame_gui.elements.UIPanel(relative_rect=pygame.Rect(0, 0, *self._size), starting_layer_height=-1, manager=self, object_id=pygame_gui.core.ObjectID("background"))
        self._all_objs.append(self.bg)
        self.title = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(30, 30, self._size[0] - 60, 50), text="EV3Sim", manager=self, object_id=pygame_gui.core.ObjectID("title"))
        self._all_objs.append(self.title)
        relative_rect = pygame.Rect(
            (self._size[0] - self.button_size[0]) / 2, (self._size[1] - self.button_size[1]) / 2, *self.button_size
        )
        self.simulate_button = pygame_gui.elements.UIButton(
            relative_rect=relative_rect,
            text="Simulate",
            manager=self,
            object_id=pygame_gui.core.ObjectID("simulate_button"),
        )
        self._all_objs.append(self.simulate_button)

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("simulate_button"):
                from ev3sim.visual.manager import ScreenObjectManager

                ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BATCH)

    def onPop(self):
        pass
