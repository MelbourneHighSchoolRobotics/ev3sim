from ev3sim.visual.manager import ScreenObjectManager
import pygame
import pygame_gui
from ev3sim.visual.menus.base_menu import BaseMenu


class UpdateMenu(BaseMenu):
    def generateObjects(self):
        # In order to respect theme changes, objects must be built in initWithKwargs
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, *self._size),
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)

        text_size = (self._size[0] / 2, self._size[1] / 2)
        self.text_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(text_size[0] / 2, text_size[1] / 2, *text_size),
            starting_layer_height=-0.5,
            manager=self,
            object_id=pygame_gui.core.ObjectID("text_background"),
        )
        self._all_objs.append(self.text_panel)

        button_ratio = 4
        button_size = (self._size[0] / 4, self._size[1] / 3)
        button_size = (
            min(button_size[0], button_size[1] * button_ratio),
            min(button_size[1], button_size[0] / button_ratio),
        )
        self.text = pygame_gui.elements.UITextBox(
            html_text=self.panel_kwargs["text"],
            relative_rect=pygame.Rect(
                text_size[0] / 2 + 30, text_size[1] / 2 + 30, text_size[0] - 60, text_size[1] - button_size[1] - 90
            ),
            manager=self,
            object_id=pygame_gui.core.ObjectID("text_dialog_workspace", "text_dialog"),
        )
        self._all_objs.append(self.text)

        self.button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                text_size[0] - button_size[0] / 2, 3 * text_size[1] / 2 - button_size[1] - 30, *button_size
            ),
            text=self.panel_kwargs["button"] or "Ok",
            manager=self,
            object_id=pygame_gui.core.ObjectID("complete_action", "menu_button"),
        )
        self.addButtonEvent("complete_action", self.clickAction)
        self._all_objs.append(self.button)
        super().generateObjects()

    def initWithKwargs(self, **kwargs):
        self.panels = kwargs["panels"]
        self.panel_index = 0
        self.panel_kwargs = self.panels[self.panel_index]
        return super().initWithKwargs(**kwargs)

    def incrementPanel(self):
        self.panel_index += 1
        if self.panel_index == len(self.panels):
            ScreenObjectManager.instance.popScreen()
        else:
            self.panel_kwargs = self.panels[self.panel_index]

    def clickAction(self):
        if self.panel_kwargs["action"]:
            self.panel_kwargs["action"]()
        self.incrementPanel()

    def onPop(self):
        pass
