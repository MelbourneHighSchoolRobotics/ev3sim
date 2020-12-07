import pygame
import pygame_gui
import yaml
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.objects import visualFactory
from ev3sim.visual.utils import screenspace_to_worldspace


class RescueMapEditMenu(BaseMenu):

    MODE_NORMAL = "NORMAL"
    MODE_TILE_DIALOG = "TILE_SELECT"

    SELECTED_NOTHING = "Nothing"
    SELECTED_GENERIC_TILE = "Tile"

    def initWithKwargs(self, **kwargs):
        self.current_mpos = (0, 0)
        self.selected_index = None
        self.selected_type = self.SELECTED_NOTHING
        self.batch_file = kwargs.get("batch_file", None)
        if self.batch_file is None:
            raise ValueError(f"batch_file are required here. Got {self.batch_file}.")
        self.mode = self.MODE_NORMAL
        with open(self.batch_file, "r") as f:
            batch = yaml.safe_load(f)
        self.previous_info = batch
        self.current_tiles = batch.get("settings", {}).get("rescue", {}).get("TILE_DEFINITIONS", [])
        super().initWithKwargs(**kwargs)
        self.resetRescueVisual()

    def getSelectedAttribute(self, attr, fallback=None, index=None):
        if index is None:
            index = self.selected_index
        return self.current_tiles[index].get(attr, fallback)

    def setSelectedAttribute(self, attr, val, index=None):
        if index is None:
            index = self.selected_index
        self.current_tiles[index][attr] = val

    tile_offset = (8, 16)

    def toTilePos(self, mpos):
        new_pos = screenspace_to_worldspace(mpos, self.customMap)
        new_pos = [new_pos[0] - self.tile_offset[0], new_pos[1] - self.tile_offset[1]]
        return int((new_pos[0] + 105) // 30 - 3), int((new_pos[1] + 105) // 30 - 3)

    def resetRescueVisual(self):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.reset()
        ScriptLoader.instance.startUp()
        ScreenObjectManager.instance.resetVisualElements()

        self.customMap = {
            "SCREEN_WIDTH": self._size[0],
            "SCREEN_HEIGHT": self._size[1],
            "MAP_WIDTH": 293.3,
            "MAP_HEIGHT": 200,
        }

        placeableArea = visualFactory(
            name="Rectangle",
            width=8 * 30,
            height=6 * 30,
            position=(15 + self.tile_offset[0], -15 + self.tile_offset[1]),
            fill="#6f6f6f",
        )
        placeableArea.customMap = self.customMap
        placeableArea.calculatePoints()
        ScreenObjectManager.instance.registerVisual(placeableArea, "placeableArea")

    def sizeObjects(self):
        # Bg
        self.side_width = self._size[0] / 6
        self.sidebar.set_dimensions((self.side_width, self._size[1] + 10))
        self.sidebar.set_position((-5, -5))

        # Clickies

        # Save/Cancel
        self.action_size = (self.side_width * 0.8, self._size[1] * 0.1)
        self.save_button.set_dimensions(self.action_size)
        self.save_button.set_position(
            (self.side_width / 2 - self.action_size[0] / 2 - 2.5, self._size[1] - self.action_size[1] * 2 - 40)
        )
        self.cancel_button.set_dimensions(self.action_size)
        self.cancel_button.set_position(
            (self.side_width / 2 - self.action_size[0] / 2 - 2.5, self._size[1] - self.action_size[1] - 20)
        )
        self.resetRescueVisual()

    def generateObjects(self):
        dummy_rect = pygame.Rect(0, 0, *self._size)

        # Bg
        self.sidebar = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-0.5,
            manager=self,
            object_id=pygame_gui.core.ObjectID("sidebar-bot-edit", "bot_edit_bar"),
        )
        self._all_objs.append(self.sidebar)

        # Save/Cancel
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="Save",
            manager=self,
            object_id=pygame_gui.core.ObjectID("save-changes", "action_button"),
        )
        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="Cancel",
            manager=self,
            object_id=pygame_gui.core.ObjectID("cancel-changes", "action_button"),
        )
        self._all_objs.append(self.save_button)
        self._all_objs.append(self.cancel_button)

    def saveBatch(self):
        for i in range(len(self.current_tiles)):
            pos = self.getSelectedAttribute("position", index=i, fallback=[0, 0])
            pos = [float(v) for v in pos]
            self.setSelectedAttribute("position", pos, index=i)
        self.previous_info["settings"]["rescue"]["TILE_DEFINITIONS"] = self.current_tiles
        with open(self.batch_file, "w") as f:
            f.write(yaml.dump(self.previous_info))

    def handleEvent(self, event):
        if self.mode == self.MODE_NORMAL:
            if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                # Removing
                if event.ui_object_id.startswith("remove_button"):
                    self.removeSelected()
                # Saving
                elif event.ui_object_id.startswith("save-changes"):
                    self.saveBatch()
                    ScreenObjectManager.instance.popScreen()
                elif event.ui_object_id.startswith("cancel-changes"):
                    ScreenObjectManager.instance.popScreen()
            elif event.type == pygame.MOUSEMOTION:
                self.current_mpos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.current_mpos[0] > self.side_width:
                    print(self.toTilePos(self.current_mpos))
            elif event.type == pygame.MOUSEWHEEL:
                for attr, conv, inc in [
                    ("rotation_entry", int, 90),
                ]:
                    if hasattr(self, attr):
                        rect = getattr(self, attr).get_relative_rect()
                        if (
                            rect.left <= self.actual_mpos[0] <= rect.right
                            and rect.top <= self.actual_mpos[1] <= rect.bottom
                        ):
                            try:
                                val = conv(getattr(self, attr).text)
                                val += event.y * inc
                                getattr(self, attr).set_text(str(val))
                            except:
                                pass
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE:
                    self.removeSelected()

    def drawOptions(self):
        self.clearOptions()
        # TODO: show side options for nothing selected, nothing on the tile, or a tile.

    def drawRemove(self):
        self.remove_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                self.side_width / 2 - self.action_size[0] / 2 - 2.5,
                self._size[1] - self.action_size[1] * 3 - 60,
                *self.action_size,
            ),
            text="Remove",
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_button", "cancel-changes"),
        )

    def clearOptions(self):
        try:
            self.remove_button.kill()
        except:
            pass

    def clearObjects(self):
        super().clearObjects()
        self.clearOptions()

    def draw_ui(self, window_surface: pygame.surface.Surface):
        if self.selected_index is not None:
            # TODO: Update tile rotation
            pass

        ScreenObjectManager.instance.applyToScreen(to_screen=window_surface)
        super().draw_ui(window_surface)

    def onPop(self):
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.world import World

        ScreenObjectManager.instance.resetVisualElements()
        World.instance.resetWorld()
        ScriptLoader.instance.reset()
