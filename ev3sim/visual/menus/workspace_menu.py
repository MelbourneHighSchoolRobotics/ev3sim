import pygame
import pygame_gui
from ev3sim.file_helper import find_abs
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.search_locations import config_locations


class WorkspaceMenu(BaseMenu):
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
            html_text="""\
In order to use ev3sim, you need to specify a <font color="#06d6a0">workspace folder</font>.<br><br>\
<font color="#4cc9f0">Bots</font> and <font color="#4cc9f0">presets</font> you create will be stored in this folder.\
""",
            relative_rect=pygame.Rect(
                text_size[0] / 2 + 30, text_size[1] / 2 + 30, text_size[0] - 60, text_size[1] - button_size[1] - 90
            ),
            manager=self,
            object_id=pygame_gui.core.ObjectID("text_dialog_workspace", "text_dialog"),
        )
        self._all_objs.append(self.text)

        self.select = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                text_size[0] - button_size[0] / 2, 3 * text_size[1] / 2 - button_size[1] - 30, *button_size
            ),
            text="Select",
            manager=self,
            object_id=pygame_gui.core.ObjectID("select_button", "menu_button"),
        )
        self.addButtonEvent("select_button", self.clickSelect)
        self._all_objs.append(self.select)
        super().generateObjects()

    def clickSelect(self):
        # Open file dialog.
        import yaml
        from ev3sim.simulation.loader import StateHandler
        from ev3sim.visual.manager import ScreenObjectManager

        def onComplete(directory):
            if not directory:
                return
            conf_file = find_abs("user_config.yaml", allowed_areas=config_locations())
            with open(conf_file, "r") as f:
                conf = yaml.safe_load(f)
            conf["app"]["workspace_folder"] = directory
            with open(conf_file, "w") as f:
                f.write(yaml.dump(conf))
            StateHandler.WORKSPACE_FOLDER = directory
            ScreenObjectManager.instance.popScreen()
            ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_MENU)

        self.addFileDialog(
            "Select Workspace",
            None,
            True,
            onComplete,
        )

    def onPop(self):
        pass
