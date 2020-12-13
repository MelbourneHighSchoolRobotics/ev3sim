import math
import pygame
import pygame_gui
import yaml
import numpy as np
import ev3sim.visual.utils as utils
from ev3sim.file_helper import find_abs
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.objects import IVisualElement, visualFactory
from ev3sim.objects.base import BaseObject
from ev3sim.search_locations import asset_locations, preset_locations


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
        if "BOT_SPAWN_POSITION" not in self.previous_info["settings"]["rescue"]:
            self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"] = [[[0, 0], 0]]
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

    def getDirsAndRotations(self, tile):
        direction = {
            "left": (-1, 0),
            "right": (1, 0),
            "up": (0, 1),
            "down": (0, -1),
        }
        rotation = {
            "left": 0,
            "right": np.pi,
            "up": -np.pi / 2,
            "down": np.pi,
        }
        if tile["flip"]:
            for key in direction:
                direction[key] = (-direction[key][0], direction[key][1])
            rotation["left"], rotation["right"] = rotation["right"], rotation["left"]
        for key in direction:
            direction[key] = (
                math.floor(
                    0.5 + direction[key][0] * np.cos(tile["rotation"]) - direction[key][1] * np.sin(tile["rotation"])
                ),
                math.floor(
                    0.5 + direction[key][0] * np.sin(tile["rotation"]) + direction[key][1] * np.cos(tile["rotation"])
                ),
            )
            rotation[key] += tile["rotation"]
        return direction, rotation

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
        remove = []
        for key in ScreenObjectManager.instance.objects:
            if key.startswith("tile-entry"):
                remove.append(key)
        for key in remove:
            ScreenObjectManager.instance.unregisterVisual(key)
        r.spawnTiles()
        for index, tile in enumerate(r.tiles):
            direction, rotation = self.getDirsAndRotations(tile)
            for i, entry_dir in enumerate(tile["entries"]):
                startArrow = visualFactory(
                    name="Polygon",
                    verts=[
                        [1.96, 0],
                        [0.21, 1.75],
                        [0.21, 0.5],
                        [-1.4, 0.5],
                        [-1.4, -0.5],
                        [0.21, -0.5],
                        [0.21, -1.75],
                        [1.96, 0],
                    ],
                    fill="#219ebc",
                    stroke_width=0,
                    zPos=0.1,
                    sensorVisible=False,
                    rotation=rotation[entry_dir],
                )
                startArrow.key = f"tile-{index}-entry-{i}"
                startArrow.position = [
                    tile["world_pos"][0] + self.tile_offset[0] + direction[entry_dir][0] * 11,
                    tile["world_pos"][1] + self.tile_offset[1] + direction[entry_dir][1] * 11,
                ]
                startArrow.customMap = self.customMap
                startArrow.calculatePoints()
                ScreenObjectManager.instance.registerVisual(startArrow, startArrow.key)

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
        self.current_tile_objects = r.tiles
        # Add an extra border around selected tile
        if self.selected_index is not None:
            hoverRect = visualFactory(
                name="Rectangle",
                width=30,
                height=30,
                position=(
                    self.tile_offset[0] + 30 * self.selected_index[0],
                    self.tile_offset[1] + 30 * self.selected_index[1],
                ),
                fill=None,
                stroke="#ff0000",
                stroke_width=1,
                zPos=20,
            )
            hoverRect.customMap = self.customMap
            hoverRect.calculatePoints()
            ScreenObjectManager.instance.registerVisual(hoverRect, "hoverRect")

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
        # Reorder the tiles so it follows a path.
        # Use the selection code to achieve this.
        self.selected_type = self.SELECTED_GENERIC_TILE
        self.selected_index = self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][0][0]
        for i in range(len(self.current_tiles)):
            self.current_tiles[i]["current_index"] = i
        entry_index = 0
        i = 0
        loops = 0
        while True:
            try:
                if self.getSelectedAttribute("list_index", None) is None:
                    self.setSelectedAttribute("list_index", i)
                    i += 1
            except:
                break
            index = self.getSelectedAttribute("current_index")
            # Move to the next tile
            dirs, _ = self.getDirsAndRotations(self.current_tile_objects[index])
            exit = self.current_tile_objects[index]["exits"][entry_index]
            self.selected_index = (
                self.selected_index[0] + dirs[exit][0],
                self.selected_index[1] + dirs[exit][1],
            )
            try:
                nindex = self.getSelectedAttribute("current_index")
            except:
                break
            ndirs, _ = self.getDirsAndRotations(self.current_tile_objects[nindex])
            for key in ndirs:
                if ndirs[key][0] == -dirs[exit][0] and ndirs[key][1] == -dirs[exit][1]:
                    entry_index = self.current_tile_objects[nindex]["entries"].index(key)
                    break
            else:
                break
            loops += 1
            if loops > len(self.current_tiles):
                break

        new_tiles = [None] * len(self.current_tiles)
        end_index = len(self.current_tiles) - 1
        for i, tile in enumerate(self.current_tiles):
            new_index = self.getSelectedAttribute("list_index", None, i)
            for delkey in ["current_index", "list_index"]:
                if delkey in tile:
                    del tile[delkey]
            if new_index is None:
                new_tiles[end_index] = tile
                end_index -= 1
            else:
                new_tiles[new_index] = tile

        self.current_tiles = new_tiles

        for i in range(len(self.current_tiles)):
            pos = self.getSelectedAttribute("position", index=i, fallback=[0, 0])
            pos = [int(v) for v in pos]
            self.setSelectedAttribute("position", pos, index=i)
        self.previous_info["settings"]["rescue"]["TILE_DEFINITIONS"] = self.current_tiles
        # Update the spawn rotation related to the tile.
        for i in range(len(self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"])):
            self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][i][1] = 0
            for obj in self.previous_info["settings"]["rescue"]["TILE_DEFINITIONS"]:
                if (
                    obj["position"][0] != self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][i][0][0]
                    or obj["position"][1] != self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][i][0][1]
                ):
                    continue
                rot = obj.get("rotation", 0)
                flip = obj.get("flip", False)
                # All tiles are by default from left to being with. Flip does so on the horizontal.
                if flip:
                    rot = 180 - rot
                self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][i][1] = rot
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
        self.resetRescueVisual()

    def placeTile(self, tile_index):
        assert self.selected_index is not None
        for i, tile in enumerate(self.current_tiles):
            if tile["position"][0] == self.selected_index[0] and tile["position"][1] == self.selected_index[1]:
                index = i
                break
        else:
            index = len(self.current_tiles)
            self.current_tiles.append({})
        self.current_tiles[index] = {
            "path": f"tiles/definitions/{self.tile_locations[tile_index]}",
            "position": self.selected_index,
            "rotation": 0,
            "flip": False,
        }
        self.selected_type = self.SELECTED_GENERIC_TILE
        self.resetRescueVisual()
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

    def setSpawnAtSelected(self):
        pos = [int(v) for v in self.getSelectedAttribute("position")]
        self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][0][0] = pos

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
                elif event.ui_object_id.startswith("tile_type"):
                    self.drawTileDialog()
                elif event.ui_object_id.startswith("spawn_button"):
                    self.setSpawnAtSelected()
                    self.updateSpawnCheckbox()
                elif event.ui_object_id.startswith("flip_button"):
                    self.setSelectedAttribute("flip", not self.getSelectedAttribute("flip", False))
                    self.updateFlipCheckbox()
                    self.resetRescueVisual()
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
                            rect.left <= self.current_mpos[0] <= rect.right
                            and rect.top <= self.current_mpos[1] <= rect.bottom
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
            self.drawRotationFlip()
            self.drawRemove()
            if "city_limits" in self.getSelectedAttribute("path"):
                self.drawSpawnOptions()

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

    def drawSpawnOptions(self):
        total_width = self.action_size[0]
        label_width = total_width * 0.7 - 10
        button_size = total_width - label_width - 10
        self.spawn_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                self.side_width / 2 - total_width / 2 - 2.5,
                30 + (self.action_size[1] + 20),
                label_width,
                button_size,
            ),
            text="Spawn",
            manager=self,
            object_id=pygame_gui.core.ObjectID("is_spawn", "entry-label"),
        )
        but_rect = pygame.Rect(
            self.side_width / 2 - total_width / 2 - 2.5 + label_width + 10,
            30 + (self.action_size[1] + 20),
            button_size,
            button_size,
        )
        self.spawn_image = pygame_gui.elements.UIImage(
            relative_rect=but_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("spawn_image"),
            image_surface=pygame.Surface((button_size, button_size)),
        )
        self.spawn_button = pygame_gui.elements.UIButton(
            relative_rect=but_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("spawn_button", "invis_button"),
        )
        self.updateSpawnCheckbox()

    def updateSpawnCheckbox(self):
        tile_pos = self.getSelectedAttribute("position")
        spawn = self.previous_info["settings"]["rescue"]["BOT_SPAWN_POSITION"][0][0]
        img = pygame.image.load(
            find_abs(
                "ui/box_check.png" if tile_pos[0] == spawn[0] and tile_pos[1] == spawn[1] else "ui/box_clear.png",
                allowed_areas=asset_locations,
            )
        )
        if img.get_size() != self.spawn_image.rect.size:
            img = pygame.transform.smoothscale(img, (self.spawn_image.rect.width, self.spawn_image.rect.height))
        self.spawn_image.set_image(img)

    def drawRotationFlip(self):
        total_height = self.action_size[1]
        label_height = total_height / 2 - 5
        entry_height = total_height / 2 - 5
        entry_width = self.action_size[0] / 2
        self.rotation_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                self.side_width / 2 - self.action_size[0] / 2 - 2.5,
                30 + 2 * (self.action_size[1] + 20),
                self.action_size[0],
                label_height,
            ),
            text="Rotation",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation_label", "entry-label"),
        )
        self.rotation_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(
                self.side_width / 2 + self.action_size[0] / 2 - entry_width - 2.5,
                30 + 2 * (self.action_size[1] + 20) + label_height + 10,
                entry_width,
                entry_height,
            ),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation_entry", "text_entry_line"),
        )
        self.rotation_entry.set_text(str(self.getSelectedAttribute("rotation", 0)))
        self.flip_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                self.side_width / 2 - self.action_size[0] / 2 - 2.5,
                30 + 3 * (self.action_size[1] + 20),
                self.action_size[0],
                label_height,
            ),
            text="Flipped",
            manager=self,
            object_id=pygame_gui.core.ObjectID("is_flip", "entry-label"),
        )
        but_rect = pygame.Rect(
            self.side_width / 2 + self.action_size[0] / 2 - 2.5 - entry_height,
            30 + 3 * (self.action_size[1] + 20) + entry_height + 10,
            entry_height,
            entry_height,
        )
        self.flip_image = pygame_gui.elements.UIImage(
            relative_rect=but_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("flip_image"),
            image_surface=pygame.Surface((entry_height, entry_height)),
        )
        self.flip_button = pygame_gui.elements.UIButton(
            relative_rect=but_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("flip_button", "invis_button"),
        )
        self.updateFlipCheckbox()

    def updateFlipCheckbox(self):
        img = pygame.image.load(
            find_abs(
                "ui/box_check.png" if self.getSelectedAttribute("flip", False) else "ui/box_clear.png",
                allowed_areas=asset_locations,
            )
        )
        if img.get_size() != self.flip_image.rect.size:
            img = pygame.transform.smoothscale(img, (self.flip_image.rect.width, self.flip_image.rect.height))
        self.flip_image.set_image(img)

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

    def clearSpawnOptions(self):
        try:
            self.spawn_label.kill()
            self.spawn_button.kill()
            self.spawn_image.kill()
        except:
            pass

    def clearRotationFlip(self):
        try:
            self.rotation_label.kill()
            self.rotation_entry.kill()
            self.flip_label.kill()
            self.flip_button.kill()
            self.flip_image.kill()
        except:
            pass

    def clearRemove(self):
        try:
            self.remove_button.kill()
        except:
            pass

    def clearOptions(self):
        self.clearTileTypeOptions()
        self.clearSpawnOptions()
        self.clearRotationFlip()
        self.clearRemove()

    def clearObjects(self):
        super().clearObjects()
        self.clearOptions()

    tile_locations = [
        "city_limits.yaml",
        "straight.yaml",
        "zig_zag.yaml",
        "right_angle.yaml",
        "double_curve.yaml",
        "strict_turns1.yaml",
        "curved_straight.yaml",
        "strict_turns2.yaml",
        "sharp_straight.yaml",
        "dotted.yaml",
        "rough.yaml",
        "ramp.yaml",
        "color_right.yaml",
        "left_circle_green.yaml",
        "square_green.yaml",
        "tunnel.yaml",
        "water_tower.yaml",
    ]

    def drawTileDialog(self):
        self.mode = self.MODE_TILE_DIALOG

        class TilePicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                super().kill()
                self.removeTileDialog()

            def process_event(self2, event: pygame.event.Event) -> bool:
                if event.type == pygame.MOUSEWHEEL:
                    self.scroll_container.vert_scroll_bar.scroll_position -= event.y * 10
                    self.scroll_container.vert_scroll_bar.scroll_position = min(
                        max(
                            self.scroll_container.vert_scroll_bar.scroll_position,
                            self.scroll_container.vert_scroll_bar.top_limit,
                        ),
                        self.scroll_container.vert_scroll_bar.bottom_limit
                        - self.scroll_container.vert_scroll_bar.sliding_button.relative_rect.height,
                    )
                    x_pos = 0
                    y_pos = (
                        self.scroll_container.vert_scroll_bar.scroll_position
                        + self.scroll_container.vert_scroll_bar.arrow_button_height
                    )
                    self.scroll_container.vert_scroll_bar.sliding_button.set_relative_position((x_pos, y_pos))
                    self.scroll_container.vert_scroll_bar.start_percentage = (
                        self.scroll_container.vert_scroll_bar.scroll_position
                        / self.scroll_container.vert_scroll_bar.scrollable_height
                    )
                    self.scroll_container.vert_scroll_bar.has_moved_recently = True
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_object_id.split(".")[-1].startswith("tile-"):
                        index = int(event.ui_object_id.split(".")[-1].split("-")[1])
                        self.placeTile(index)
                        self2.kill()
                        return True
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, self._size[1] * 0.7)
        self.picker = TilePicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="Pick Tile Type",
            object_id=pygame_gui.core.ObjectID("tile_dialog"),
        )

        button_size = (picker_size[0] - 120) / 3
        button_pos = lambda i: ((button_size + 15) * (i % 3), 10 + (button_size + 15) * (i // 3))

        self.tile_buttons = []
        self.tile_images = []
        self.scroll_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect(20, 10, picker_size[0] - 60, picker_size[1] - 80),
            container=self.picker,
            manager=self,
        )
        for i in range(len(self.tile_locations)):
            rect = pygame.Rect(*button_pos(i), button_size, button_size)
            self.tile_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=rect,
                    text=f"{i}",
                    manager=self,
                    container=self.scroll_container,
                    object_id=pygame_gui.core.ObjectID(f"tile-{i}-button", "invis_button"),
                )
            )
            with open(find_abs(f"tiles/definitions/{self.tile_locations[i]}", preset_locations), "r") as f:
                conf = yaml.safe_load(f)
            self.tile_images.append(
                pygame_gui.elements.UIImage(
                    relative_rect=rect,
                    image_surface=pygame.image.load(find_abs(conf["preview"], preset_locations)),
                    manager=self,
                    container=self.scroll_container,
                    object_id=pygame_gui.core.ObjectID(f"tile-{i}-image"),
                )
            )
        self.scroll_container.set_scrollable_area_dimensions(
            (picker_size[0] - 80, (button_size + 15) * ((len(self.tile_locations) + 2) // 3))
        )

    def removeTileDialog(self):
        try:
            self.mode = self.MODE_NORMAL
            self.scroll_container.kill()
            for but, img in zip(self.tile_buttons, self.tile_images):
                but.kill()
                img.kill()
        except:
            pass

    def draw_ui(self, window_surface: pygame.surface.Surface):
        if self.selected_index is not None:
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_GENERIC_TILE:
                try:
                    rot = int(self.rotation_entry.text)
                    old_rot = self.getSelectedAttribute("rotation", 0)
                    if rot != old_rot:
                        self.setSelectedAttribute("rotation", rot)
                        self.resetRescueVisual()
                except:
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
