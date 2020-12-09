import pygame
import pygame_gui
import yaml
import ev3sim.visual.utils as utils
from ev3sim.file_helper import find_abs
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.objects import IVisualElement, visualFactory
from ev3sim.objects.base import BaseObject
from ev3sim.search_locations import preset_locations


class RescueMapEditMenu(BaseMenu):

    MODE_NORMAL = "NORMAL"
    MODE_TILE_DIALOG = "TILE_SELECT"

    SELECTED_NOTHING = "Nothing"
    SELECTED_EMPTY = "Empty"
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
        self.drawOptions()

    def getSelectedAttribute(self, attr, fallback=None, index=None):
        if index is None:
            assert self.selected_type == self.SELECTED_GENERIC_TILE
            for i, tile in enumerate(self.current_tiles):
                if tile["position"][0] == self.selected_index[0] and tile["position"][1] == self.selected_index[1]:
                    index = i
                    break
            else:
                raise ValueError(f"Expected existing tile in position {self.selected_index}")
        return self.current_tiles[index].get(attr, fallback)

    def setSelectedAttribute(self, attr, val, index=None):
        if index is None:
            assert self.selected_type == self.SELECTED_GENERIC_TILE
            for i, tile in enumerate(self.current_tiles):
                if tile["position"][0] == self.selected_index[0] and tile["position"][1] == self.selected_index[1]:
                    index = i
                    break
            else:
                raise ValueError(f"Expected existing tile in position {self.selected_index}")
        self.current_tiles[index][attr] = val

    tile_offset = (8, 16)

    def toTilePos(self, mpos):
        new_pos = utils.screenspace_to_worldspace(mpos, self.customMap)
        new_pos = [new_pos[0] - self.tile_offset[0], new_pos[1] - self.tile_offset[1]]
        return int((new_pos[0] + 105) // 30 - 3), int((new_pos[1] + 105) // 30 - 3)

    def resetRescueVisual(self):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.presets.rescue import RescueInteractor

        ScriptLoader.instance.reset()
        ScriptLoader.instance.startUp()
        ScreenObjectManager.instance.resetVisualElements()
        with open(find_abs("rescue.yaml", preset_locations), "r") as f:
            conf = yaml.safe_load(f)
        utils.GLOBAL_COLOURS.update(conf.get("colours", {}))

        r = RescueInteractor()
        r.TILE_DEFINITIONS = self.current_tiles
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
        r.spawnTiles()
        for tile in r.tiles:
            for obj in tile["all_elems"]:
                obj.position = [
                    obj.position[0] + self.tile_offset[0],
                    obj.position[1] + self.tile_offset[1],
                ]
                if isinstance(obj, IVisualElement):
                    obj.customMap = self.customMap
                    obj.calculatePoints()
                elif isinstance(obj, BaseObject):
                    obj.visual.customMap = self.customMap
                    obj.visual.calculatePoints()

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

    def selectTile(self, pos):
        self.selected_index = pos
        for tile in self.current_tiles:
            if tile["position"][0] == self.selected_index[0] and tile["position"][1] == self.selected_index[1]:
                self.selected_type = self.SELECTED_GENERIC_TILE
                break
        else:
            self.selected_type = self.SELECTED_EMPTY
        self.drawOptions()

    def removeSelected(self):
        for i, tile in enumerate(self.current_tiles):
            if tile["position"][0] == self.selected_index[0] and tile["position"][1] == self.selected_index[1]:
                index = i
                break
        else:
            raise ValueError("No existing tile is selected!")
        del self.current_tiles[index]
        self.selected_index = None
        self.selected_type = self.SELECTED_NOTHING
        self.resetRescueVisual()
        self.drawOptions()

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
                    self.selectTile(self.toTilePos(self.current_mpos))
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
        if self.selected_type != self.SELECTED_NOTHING:
            self.drawTileTypeOptions()
        if self.selected_type not in [self.SELECTED_NOTHING, self.SELECTED_EMPTY]:
            self.drawRemove()

    def drawTileTypeOptions(self):
        self.tile_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                self.side_width / 2 - self.action_size[0] / 2 - 2.5,
                30,
                *self.action_size,
            ),
            text="Tile Type",
            manager=self,
            object_id=pygame_gui.core.ObjectID("tile_type", "any_button"),
        )

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

    def clearTileTypeOptions(self):
        try:
            self.tile_button.kill()
        except:
            pass

    def clearRemove(self):
        try:
            self.remove_button.kill()
        except:
            pass

    def clearOptions(self):
        self.clearTileTypeOptions()
        self.clearRemove()

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
