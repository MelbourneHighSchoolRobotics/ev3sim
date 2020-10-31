import os.path
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.visual.menus.base_menu import BaseMenu


class BatchMenu(BaseMenu):
    def sizeObjects(self):
        button_size = self._size[0] / 4, 40
        batch_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].set_dimensions(button_size)
            self.batch_buttons[i].set_position(batch_rect(i))

    def generateObjects(self):
        dummy_rect = pygame.Rect(0, 0, *self._size)
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)
        # Find all batch files and show them
        self.available_batches = []
        for rel_dir in ["package", "package/batched_commands/"]:
            actual_dir = find_abs_directory(rel_dir)
            for batch in BatchValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_batches.append((batch[:-5], os.path.join(actual_dir, batch)))
        self.batch_buttons = []
        for i, (show, batch) in enumerate(self.available_batches):
            self.batch_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=dummy_rect,
                    text=show,
                    manager=self,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "batch_select_button"),
                )
            )
        self._all_objs.extend(self.batch_buttons)

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            batch_index = int(event.ui_object_id.split("#")[0].split("-")[-1])
            from ev3sim.visual.manager import ScreenObjectManager

            ScreenObjectManager.instance.pushScreen(
                ScreenObjectManager.SCREEN_SIM, batch=self.available_batches[batch_index][1]
            )

    def onPop(self):
        pass
