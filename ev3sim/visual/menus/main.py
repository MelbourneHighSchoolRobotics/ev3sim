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
        button_size = self._size[0] / 4, self._size[1] / 6
        relative_rect = pygame.Rect(
            self._size[0] / 2 - button_size[0] / 2, self._size[1] / 2 - button_size[1], *button_size
        )
        self.hello_button = pygame_gui.elements.UIButton(
            relative_rect=relative_rect,
            text="Click me!",
            manager=self,
            object_id=pygame_gui.core.ObjectID("hello", "menu_button"),
        )

    def initWithKwargs(self, **kwargs):
        pass

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("hello"):
                from ev3sim.visual.manager import ScreenObjectManager

                ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BATCH)

    def onPop(self):
        pass
