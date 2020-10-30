import os.path
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs_directory
from ev3sim.validation.batch_files import BatchValidator


class BatchMenu(pygame_gui.UIManager):
    def __init__(self, size, *args, **kwargs):
        self._size = size
        self._batch_buttons = []
        super().__init__(size, *args, **kwargs)
        self._button_size = self._size[0] / 4, 40

    def initWithKwargs(self, **kwargs):
        # Remove all the previous buttons.
        for button in self._batch_buttons:
            button.kill()
        self._batch_buttons = []
        # Find all batch files and show them
        self.available_batches = []
        for rel_dir in ["package", "package/batched_commands/"]:
            actual_dir = find_abs_directory(rel_dir)
            for batch in BatchValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_batches.append((batch[:-5], os.path.join(actual_dir, batch)))
        for i, (show, batch) in enumerate(self.available_batches):
            relative_rect = pygame.Rect(
                self._size[0] / 10, self._size[1] / 10 + i * self._button_size[1] * 1.5, *self._button_size
            )
            self._batch_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=relative_rect,
                    text=show,
                    manager=self,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "batch_select_button"),
                )
            )

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            batch_index = int(event.ui_object_id.split("#")[0].split("-")[-1])
            from ev3sim.visual.manager import ScreenObjectManager

            ScreenObjectManager.instance.pushScreen(
                ScreenObjectManager.SCREEN_SIM, batch=self.available_batches[batch_index][1]
            )

    def onPop(self):
        pass
