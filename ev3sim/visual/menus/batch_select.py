import os.path
from ev3sim.file_helper import find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
import pygame_menu
from pygame_menu.locals import ALIGN_LEFT
from pygame_menu.widgets.widget.button import Button


def add_button_for_batch(menu: pygame_menu.Menu, show, batch_file):
    def simulate_batch():
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(ScreenObjectManager.instance.SCREEN_SIM, batch=batch_file)

    b = Button(show, batch_file, None, simulate_batch)
    attributes = menu._filter_widget_attributes({"align": ALIGN_LEFT})
    menu._configure_widget(widget=b, **attributes)
    menu._append_widget(b)


class BatchMenu(pygame_menu.Menu):
    def initWithKwargs(self, **kwargs):
        # Find all batch files and show them
        self.available_batches = []
        for rel_dir in ["package", "package/batched_commands/"]:
            actual_dir = find_abs_directory(rel_dir)
            for batch in BatchValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_batches.append((batch[:-5], os.path.join(actual_dir, batch)))
        for show, batch in self.available_batches:
            add_button_for_batch(self, show, batch)

    def onPop(self):
        pass
