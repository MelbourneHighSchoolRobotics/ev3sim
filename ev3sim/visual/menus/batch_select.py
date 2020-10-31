import os.path
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.visual.menus.base_menu import BaseMenu


class BatchMenu(BaseMenu):
    def sizeObjects(self):
        button_size = self._size[0] / 4, 40
        start_size = self._size[0] / 4, min(self._size[1] / 4, 120)
        batch_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].set_dimensions(button_size)
            self.batch_buttons[i].set_position(batch_rect(i))
        self.start_button.set_dimensions(start_size)
        self.start_button.set_position((self._size[0] * 0.9 - start_size[0], self._size[1] * 0.9 - start_size[1]))

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
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="START",
            manager=self,
            object_id=pygame_gui.core.ObjectID("start-sim"),
        )
        self._all_objs.append(self.start_button)

    def initWithKwargs(self, **kwargs):
        super().initWithKwargs(**kwargs)
        self.batch_index = -1
        self.start_button.disable()

    def clickStart(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SIM, batch=self.available_batches[self.batch_index][1]
        )

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("start-sim"):
                self.clickStart()
            else:
                self.setBatchIndex(int(event.ui_object_id.split("#")[0].split("-")[-1]))
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBatchIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBatchIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickStart()

    def setBatchIndex(self, new_index):
        self.batch_index = new_index
        # Update theming.
        self.start_button.enable()
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].combined_element_ids[1] = (
                "batch_select_button_highlighted" if i == self.batch_index else "batch_select_button"
            )
            self.batch_buttons[i].rebuild_from_changed_theme_data()

    def incrementBatchIndex(self, amount):
        if self.batch_index == -1:
            new_index = amount if amount < 0 else amount - 1
        else:
            new_index = self.batch_index + amount
        new_index %= len(self.batch_buttons)
        self.setBatchIndex(new_index)

    def onPop(self):
        pass
