import pygame
import pygame_gui
import pymunk
import yaml
import numpy as np
from ev3sim.file_helper import find_abs
from ev3sim.objects.base import STATIC_CATEGORY
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace


class BotEditMenu(BaseMenu):

    MODE_DIALOG_DEVICE = "DEVICE_SELECT"
    MODE_NORMAL = "NORMAL"
    MODE_COLOUR_DIALOG = "COLOUR"

    SELECTED_CIRCLE = "CIRCLE"
    SELECTED_POLYGON = "POLYGON"
    SELECTED_NOTHING = "NOTHING"

    def initWithKwargs(self, **kwargs):
        self.current_mpos = (0, 0)
        self.selected_index = None
        self.selected_type = self.SELECTED_NOTHING
        self.bot_file = kwargs.get("bot_file", None)
        self.lock_grid = True
        self.grid_size = 5
        self.mode = self.MODE_NORMAL
        with open(self.bot_file, "r") as f:
            bot = yaml.safe_load(f)
        self.current_object = bot["base_plate"]
        self.current_object["type"] = "object"
        self.current_object["physics"] = True
        self.current_holding = None
        super().initWithKwargs(**kwargs)
        self.setVisualElements()

    def setVisualElements(self):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.loader import ScriptLoader
        from ev3sim.simulation.world import World

        ScriptLoader.instance.startUp()
        ScreenObjectManager.instance.resetVisualElements()
        World.instance.resetWorld()
        mSize = min(*self.surf_size)
        elems = ScriptLoader.instance.loadElements([self.current_object], preview_mode=True)
        self.robot = elems[0]
        World.instance.registerObject(self.robot)
        self.customMap = {
            "SCREEN_WIDTH": self.surf_size[0],
            "SCREEN_HEIGHT": self.surf_size[1],
            "MAP_WIDTH": int(self.surf_size[0] / mSize * 24),
            "MAP_HEIGHT": int(self.surf_size[1] / mSize * 24),
        }
        while elems:
            new_elems = []
            for elem in elems:
                elem.visual.customMap = self.customMap
                elem.visual.calculatePoints()
                new_elems.extend(elem.children)
            elems = new_elems

    def placeHolding(self, pos):
        obj = {
            "physics": True,
            "type": "object",
            "visual": self.current_holding_kwargs.copy(),
            "position": pos,
            "restitution": 0.2,
            "friction": 0.8,
        }
        self.current_object["children"].append(obj)
        self.setVisualElements()
        self.generateHoldingItem()

    def selectObj(self, pos):
        from ev3sim.simulation.world import World

        shapes = World.instance.space.point_query(
            pos, 0.0, pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS ^ STATIC_CATEGORY)
        )
        if shapes:
            top_shape_z = max(map(lambda x: x.shape.actual_obj.visual.zPos, shapes))
            top_shape = list(filter(lambda x: x.shape.actual_obj.visual.zPos == top_shape_z, shapes))
            assert len(top_shape) == 1
            self.selected_index = self.robot.children.index(top_shape[0].shape.actual_obj)
            if self.current_object["children"][self.selected_index]["visual"]["name"] == "Circle":
                self.selected_type = self.SELECTED_CIRCLE
            elif self.current_object["children"][self.selected_index]["visual"]["name"] == "Polygon":
                self.selected_type = self.SELECTED_POLYGON
            self.drawOptions()

    def sizeObjects(self):
        # Bg
        self.side_width = self._size[0] / 6
        self.bot_height = self._size[1] / 6
        self.sidebar.set_dimensions((self.side_width, self._size[1] + 10))
        self.sidebar.set_position((-5, -5))
        self.bot_bar.set_dimensions((self._size[0] - self.side_width + 20, self.bot_height))
        self.bot_bar.set_position((-10 + self.side_width, self._size[1] - self.bot_height + 5))

        # Clickies
        icon_size = self.side_width / 2
        self.select_icon.set_dimensions((icon_size, icon_size))
        self.select_icon.set_position((self.side_width / 2 - icon_size / 2, 50))
        self.select_button.set_dimensions((icon_size, icon_size))
        self.select_button.set_position((self.side_width / 2 - icon_size / 2, 50))
        self.circle_icon.set_dimensions((icon_size, icon_size))
        self.circle_icon.set_position((self.side_width / 2 - icon_size / 2, 50 + icon_size * 1.5))
        self.circle_button.set_dimensions((icon_size, icon_size))
        self.circle_button.set_position((self.side_width / 2 - icon_size / 2, 50 + icon_size * 1.5))
        self.polygon_icon.set_dimensions((icon_size, icon_size))
        self.polygon_icon.set_position((self.side_width / 2 - icon_size / 2, 50 + icon_size * 3))
        self.polygon_button.set_dimensions((icon_size, icon_size))
        self.polygon_button.set_position((self.side_width / 2 - icon_size / 2, 50 + icon_size * 3))
        self.device_icon.set_dimensions((icon_size, icon_size))
        self.device_icon.set_position((self.side_width / 2 - icon_size / 2, 50 + icon_size * 4.5))
        self.device_button.set_dimensions((icon_size, icon_size))
        self.device_button.set_position((self.side_width / 2 - icon_size / 2, 50 + icon_size * 4.5))

        # Other options
        lock_size = self.side_width / 4
        self.lock_grid_label.set_dimensions(((self.side_width - 30) - lock_size - 5, lock_size))
        self.lock_grid_label.set_position((10, self._size[1] - lock_size - 60))
        self.lock_grid_image.set_dimensions((lock_size, lock_size))
        self.lock_grid_image.set_position((self.side_width - lock_size - 20, self._size[1] - lock_size - 60))
        self.lock_grid_button.set_dimensions((lock_size, lock_size))
        self.lock_grid_button.set_position((self.side_width - lock_size - 20, self._size[1] - lock_size - 60))
        self.updateCheckbox()
        self.grid_size_label.set_dimensions(((self.side_width - 30) - lock_size - 5, lock_size))
        self.grid_size_label.set_position((10, self._size[1] - lock_size - 15))
        self.grid_size_entry.set_dimensions((lock_size, lock_size))
        self.grid_size_entry.set_position((self.side_width - lock_size - 20, self._size[1] - lock_size - 15))

        # Simulator objects
        self.surf_size = (self._size[0] - self.side_width + 5, self._size[1] - self.bot_height + 5)
        self.bot_screen = pygame.Surface(self.surf_size)

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
        self.bot_bar = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-0.5,
            manager=self,
            object_id=pygame_gui.core.ObjectID("botbar-bot-edit", "bot_edit_bar"),
        )
        self._all_objs.append(self.bot_bar)

        # Clickies
        self.select_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("select-button", "invis_button"),
        )
        select_icon_path = find_abs("ui/icon_select.png", allowed_areas=["package/assets/"])
        self.select_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(select_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("select-icon"),
        )
        self._all_objs.append(self.select_button)
        self._all_objs.append(self.select_icon)
        self.circle_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("circle-button", "invis_button"),
        )
        circ_icon_path = find_abs("ui/icon_circle.png", allowed_areas=["package/assets/"])
        self.circle_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(circ_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("circle-icon"),
        )
        self._all_objs.append(self.circle_button)
        self._all_objs.append(self.circle_icon)
        self.polygon_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("polygon-button", "invis_button"),
        )
        polygon_icon_path = find_abs("ui/icon_polygon.png", allowed_areas=["package/assets/"])
        self.polygon_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(polygon_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("polygon-icon"),
        )
        self._all_objs.append(self.polygon_button)
        self._all_objs.append(self.polygon_icon)
        self.device_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("device-button", "invis_button"),
        )
        device_icon_path = find_abs("ui/icon_device.png", allowed_areas=["package/assets/"])
        self.device_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(device_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("device-icon"),
        )
        self._all_objs.append(self.device_button)
        self._all_objs.append(self.device_icon)

        # Other options
        self.lock_grid_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Lock Grid",
            manager=self,
            object_id=pygame_gui.core.ObjectID("lock_grid-label", "bot_edit_label"),
        )
        self.lock_grid_image = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            manager=self,
            image_surface=pygame.Surface((dummy_rect.width, dummy_rect.height)),
            object_id=pygame_gui.core.ObjectID("lock_grid-image"),
        )
        self.lock_grid_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID(f"lock_grid-button", "checkbox-button"),
            text="",
        )
        self._all_objs.append(self.lock_grid_label)
        self._all_objs.append(self.lock_grid_image)
        self._all_objs.append(self.lock_grid_button)
        self.grid_size_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Grid Size",
            manager=self,
            object_id=pygame_gui.core.ObjectID("grid_size-label", "bot_edit_label"),
        )
        self.grid_size_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("grid_size-entry", "num_entry"),
        )
        self.grid_size_entry.set_text(str(self.grid_size))
        self._all_objs.append(self.grid_size_label)
        self._all_objs.append(self.grid_size_entry)

    def generateHoldingItem(self):
        from ev3sim.visual.objects import visualFactory

        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")

        self.current_holding = visualFactory(**self.current_holding_kwargs)
        self.current_holding.customMap = self.customMap
        self.current_holding.position = self.current_mpos
        ScreenObjectManager.instance.registerVisual(self.current_holding, "holding")

    def clickSelect(self):
        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")
        self.current_holding = None
        self.selected_type = self.SELECTED_NOTHING
        self.selected_index = -1
        self.clearSelection()

    def clickCircle(self):
        self.current_holding_kwargs = {
            "type": "visual",
            "name": "Circle",
            "radius": 1,
            "fill": "#878E88",
            "stroke_width": 0.1,
            "stroke": "#ffffff",
            "zPos": 5,
        }
        self.selected_index = "holding"
        self.selected_type = self.SELECTED_CIRCLE
        self.drawOptions()
        self.generateHoldingItem()

    def clickPolygon(self):
        self.current_holding_kwargs = {
            "type": "visual",
            "name": "Polygon",
            "fill": "#878E88",
            "stroke_width": 0.1,
            "stroke": "#ffffff",
            "verts": [
                (np.sin(0), np.cos(0)),
                (np.sin(2 * np.pi / 5), np.cos(2 * np.pi / 5)),
                (np.sin(4 * np.pi / 5), np.cos(4 * np.pi / 5)),
                (np.sin(6 * np.pi / 5), np.cos(6 * np.pi / 5)),
                (np.sin(8 * np.pi / 5), np.cos(8 * np.pi / 5)),
            ],
            "zPos": 5,
        }
        self.selected_index = "holding"
        self.selected_type = self.SELECTED_POLYGON
        self.drawOptions()
        self.generateHoldingItem()

    def updateCheckbox(self):
        img = pygame.image.load(
            find_abs("ui/box_check.png" if self.lock_grid else "ui/box_clear.png", allowed_areas=["package/assets/"])
        )
        if img.get_size() != self.lock_grid_image.rect.size:
            img = pygame.transform.smoothscale(img, (self.lock_grid_image.rect.width, self.lock_grid_image.rect.height))
        self.lock_grid_image.set_image(img)

    def handleEvent(self, event):
        if self.mode == self.MODE_NORMAL:
            if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_object_id.startswith("select-button"):
                    self.clickSelect()
                elif event.ui_object_id.startswith("circle-button"):
                    self.clickCircle()
                elif event.ui_object_id.startswith("polygon-button"):
                    self.clickPolygon()
                elif event.ui_object_id.startswith("lock_grid-button"):
                    self.lock_grid = not self.lock_grid
                    self.updateCheckbox()
                # Colour
                elif event.ui_object_id.startswith("stroke_colour-button"):
                    self.colour_field = "stroke"
                    self.addColourPicker("Pick Stroke", self.current_holding_kwargs["stroke"])
                elif event.ui_object_id.startswith("fill_colour-button"):
                    self.colour_field = "fill"
                    self.addColourPicker("Pick Fill", self.current_holding_kwargs["fill"])
            elif event.type == pygame.MOUSEMOTION:
                self.current_mpos = screenspace_to_worldspace(
                    (event.pos[0] - self.side_width, event.pos[1]), customScreen=self.customMap
                )
                if self.current_holding is not None:
                    self.current_holding.position = self.current_mpos
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mpos = screenspace_to_worldspace(
                    (event.pos[0] - self.side_width, event.pos[1]), customScreen=self.customMap
                )
                if (
                    -self.customMap["MAP_WIDTH"] / 2 <= mpos[0] <= self.customMap["MAP_WIDTH"] / 2
                    and -self.customMap["MAP_HEIGHT"] / 2 <= mpos[1] <= self.customMap["MAP_HEIGHT"] / 2
                ):
                    if self.current_holding is None:
                        self.selectObj(mpos)
                    else:
                        self.placeHolding(mpos)

    def drawOptions(self):
        self.clearSelection()
        if self.selected_index == "holding":
            obj = self.current_holding_kwargs["name"]
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            obj = self.current_object["children"][self.selected_index]["visual"]["name"]
        else:
            obj = ""
        if obj == "Circle":
            self.drawCircleOptions()
        elif obj == "Polygon":
            self.drawPolygonOptions()

    def drawCircleOptions(self):
        dummy_rect = pygame.Rect(0, 0, *self._size)

        # Radius
        self.radius_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Radius",
            manager=self,
            object_id=pygame_gui.core.ObjectID("radius-label", "bot_edit_label"),
        )
        self.radius_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("radius-entry", "num_entry"),
        )
        if self.selected_index == "holding":
            self.radius_entry.set_text(str(self.current_holding_kwargs["radius"]))
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            self.radius_entry.set_text(str(self.current_object["children"][self.selected_index]["visual"]["radius"]))
        entry_size = self.side_width / 3
        self.radius_label.set_dimensions(((self.side_width - 30) - entry_size - 5, entry_size))
        self.radius_label.set_position((self.side_width + 20, self._size[1] - self.bot_height + 15))
        self.radius_entry.set_dimensions((entry_size, entry_size))
        self.radius_entry.set_position((2 * self.side_width - 10, self._size[1] - self.bot_height + 20))

        # Stroke width
        self.stroke_num_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Stroke",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-label", "bot_edit_label"),
        )
        self.stroke_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-entry", "num_entry"),
        )
        if self.selected_index == "holding":
            self.stroke_entry.set_text(str(self.current_holding_kwargs["stroke_width"]))
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            self.stroke_entry.set_text(
                str(self.current_object["children"][self.selected_index]["visual"]["stroke_width"])
            )
        self.stroke_num_label.set_dimensions(((self.side_width - 30) - entry_size - 5, entry_size))
        self.stroke_num_label.set_position((self.side_width + 20, self._size[1] - entry_size))
        self.stroke_entry.set_dimensions((entry_size, entry_size))
        self.stroke_entry.set_position((2 * self.side_width - 10, self._size[1] - entry_size + 5))

        self.generateColourPickers()
        button_size = entry_size * 0.9
        self.fill_label.set_dimensions((self.side_width - entry_size + 5, entry_size))
        self.fill_label.set_position((2 * self.side_width + 60, self._size[1] - entry_size))
        self.fill_img.set_dimensions((button_size, button_size))
        self.fill_img.set_position(
            (3 * self.side_width + 30, self._size[1] - button_size - (entry_size - button_size) / 2)
        )
        self.stroke_label.set_dimensions((self.side_width - entry_size + 5, entry_size))
        self.stroke_label.set_position((2 * self.side_width + 60, self._size[1] - self.bot_height + 15))
        self.stroke_img.set_dimensions((button_size, button_size))
        self.stroke_img.set_position(
            (3 * self.side_width + 30, self._size[1] - self.bot_height + 15 + (entry_size - button_size) / 2)
        )

    def drawPolygonOptions(self):
        dummy_rect = pygame.Rect(0, 0, *self._size)

        # Sides
        self.sides_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Sides",
            manager=self,
            object_id=pygame_gui.core.ObjectID("sides-label", "bot_edit_label"),
        )
        self.sides_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("sides-entry", "num_entry"),
        )
        if self.selected_index == "holding":
            self.sides_entry.set_text(str(len(self.current_holding_kwargs["verts"])))
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            self.sides_entry.set_text(str(len(self.current_object["children"][self.selected_index]["visual"]["verts"])))
        entry_size = self.side_width / 3
        self.sides_label.set_dimensions(((self.side_width - 30) - entry_size - 5, entry_size))
        self.sides_label.set_position((self.side_width + 20, self._size[1] - self.bot_height + 15))
        self.sides_entry.set_dimensions((entry_size, entry_size))
        self.sides_entry.set_position((2 * self.side_width - 10, self._size[1] - self.bot_height + 20))

        # Size
        self.size_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Size",
            manager=self,
            object_id=pygame_gui.core.ObjectID("size-label", "bot_edit_label"),
        )
        self.size_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("size-entry", "num_entry"),
        )

        if self.selected_index == "holding":
            self.size_entry.set_text(str(np.linalg.norm(self.current_holding_kwargs["verts"][0], 2)))
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            self.size_entry.set_text(
                str(np.linalg.norm(self.current_object["children"][self.selected_index]["visual"]["verts"][0], 2))
            )
        self.size_label.set_dimensions(((self.side_width - 30) - entry_size - 5, entry_size))
        self.size_label.set_position((self.side_width + 20, self._size[1] - entry_size))
        self.size_entry.set_dimensions((entry_size, entry_size))
        self.size_entry.set_position((2 * self.side_width - 10, self._size[1] - entry_size + 5))

        self.generateColourPickers()
        button_size = entry_size * 0.9
        self.fill_label.set_dimensions((self.side_width - entry_size + 5, entry_size))
        self.fill_label.set_position((2 * self.side_width + 60, self._size[1] - entry_size))
        self.fill_img.set_dimensions((button_size, button_size))
        self.fill_img.set_position(
            (3 * self.side_width + 30, self._size[1] - button_size - (entry_size - button_size) / 2)
        )
        self.stroke_label.set_dimensions((self.side_width - entry_size + 5, entry_size))
        self.stroke_label.set_position((2 * self.side_width + 60, self._size[1] - self.bot_height + 15))
        self.stroke_img.set_dimensions((button_size, button_size))
        self.stroke_img.set_position(
            (3 * self.side_width + 30, self._size[1] - self.bot_height + 15 + (entry_size - button_size) / 2)
        )

        # Rotation
        self.rotation_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Rotation",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-label", "bot_edit_label"),
        )
        self.rotation_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("rotation-entry", "num_entry"),
        )
        # Takeaway pi/2, so that pointing up is rotation 0.
        if self.selected_index == "holding":
            cur_rotation = (
                np.arctan2(self.current_holding_kwargs["verts"][0][1], self.current_holding_kwargs["verts"][0][0])
                - np.pi / 2
            )
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            cur_rotation = (
                np.arctan2(
                    self.current_object["children"][self.selected_index]["visual"]["verts"][0][1],
                    self.current_object["children"][self.selected_index]["visual"]["verts"][0][0],
                )
                - np.pi / 2
            )
        while cur_rotation < 0:
            cur_rotation += np.pi
        self.rotation_entry.set_text(str(180 / np.pi * cur_rotation))
        self.rotation_label.set_dimensions(((self.side_width - 30) - entry_size - 5, entry_size))
        self.rotation_label.set_position((3 * self.side_width + 100, self._size[1] - self.bot_height + 15))
        self.rotation_entry.set_dimensions((entry_size, entry_size))
        self.rotation_entry.set_position((4 * self.side_width + 70, self._size[1] - self.bot_height + 20))
        # Stroke width
        self.stroke_num_label = pygame_gui.elements.UILabel(
            relative_rect=dummy_rect,
            text="Stroke",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-label", "bot_edit_label"),
        )
        self.stroke_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke-entry", "num_entry"),
        )
        if self.selected_index == "holding":
            self.stroke_entry.set_text(str(self.current_holding_kwargs["stroke_width"]))
        elif 0 <= self.selected_index < len(self.current_object["children"]):
            self.stroke_entry.set_text(
                str(self.current_object["children"][self.selected_index]["visual"]["stroke_width"])
            )
        self.stroke_entry.set_text(str(self.current_holding_kwargs["stroke_width"]))
        self.stroke_num_label.set_dimensions(((self.side_width - 30) - entry_size - 5, entry_size))
        self.stroke_num_label.set_position((3 * self.side_width + 100, self._size[1] - entry_size))
        self.stroke_entry.set_dimensions((entry_size, entry_size))
        self.stroke_entry.set_position((4 * self.side_width + 70, self._size[1] - entry_size + 5))

    def generateColourPickers(self):
        # Colour pickers
        self.stroke_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, *self._size),
            text="Stroke Colour",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke_colour-label", "bot_edit_label"),
        )
        self.stroke_img = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, *self._size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("stroke_colour-button"),
        )
        self.fill_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, *self._size),
            text="Fill Colour",
            manager=self,
            object_id=pygame_gui.core.ObjectID("fill_colour-label", "bot_edit_label"),
        )
        self.fill_img = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, *self._size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("fill_colour-button"),
        )
        data = {
            "fill_colour-button": {
                "colours": {
                    "normal_bg": self.current_holding_kwargs["fill"],
                    "hovered_bg": self.current_holding_kwargs["fill"],
                    "active_bg": self.current_holding_kwargs["fill"],
                }
            },
            "stroke_colour-button": {
                "colours": {
                    "normal_bg": self.current_holding_kwargs["stroke"],
                    "hovered_bg": self.current_holding_kwargs["stroke"],
                    "active_bg": self.current_holding_kwargs["stroke"],
                }
            },
        }
        self.ui_theme._load_element_colour_data_from_theme("colours", "fill_colour-button", data)
        self.fill_img.rebuild_from_changed_theme_data()
        self.ui_theme._load_element_colour_data_from_theme("colours", "stroke_colour-button", data)
        self.stroke_img.rebuild_from_changed_theme_data()

    def addColourPicker(self, title, start_colour):
        from ev3sim.visual.utils import rgb_to_hex

        self.mode = self.MODE_COLOUR_DIALOG

        class ColourPicker(pygame_gui.windows.UIColourPickerDialog):
            def process_event(self2, event: pygame.event.Event) -> bool:
                consumed_event = pygame_gui.elements.UIWindow.process_event(self2, event)
                if (
                    event.type == pygame.USEREVENT
                    and event.user_type == pygame_gui.UI_BUTTON_PRESSED
                    and event.ui_element == self2.cancel_button
                ):
                    self.removeColourPicker()
                    return consumed_event

                if (
                    event.type == pygame.USEREVENT
                    and event.user_type == pygame_gui.UI_BUTTON_PRESSED
                    and event.ui_element == self2.ok_button
                ):
                    new_col = rgb_to_hex(
                        self2.red_channel.current_value,
                        self2.green_channel.current_value,
                        self2.blue_channel.current_value,
                    )
                    if self.selected_index == "holding":
                        self.current_holding_kwargs[self.colour_field] = new_col
                        self.generateHoldingItem()
                    self.removeColourPicker()
                    return consumed_event

                return super().process_event(event)

        self.picker = ColourPicker(
            rect=pygame.Rect(self._size[0] / 4, self._size[1] / 4, self._size[0] * 0.7, self._size[1] * 0.7),
            manager=self,
            initial_colour=pygame.Color(start_colour),
            window_title=title,
            object_id=pygame_gui.core.ObjectID("colour_dialog"),
        )

    def removeColourPicker(self):
        try:
            self.picker.kill()
            self.mode = self.MODE_NORMAL
            self.drawOptions()
        except:
            pass

    def removeColourOptions(self):
        try:
            self.fill_label.kill()
            self.fill_img.kill()
            self.stroke_label.kill()
            self.stroke_img.kill()
        except:
            pass

    def removeCircleOptions(self):
        try:
            self.radius_label.kill()
            self.radius_entry.kill()
            self.stroke_num_label.kill()
            self.stroke_entry.kill()
        except:
            pass

    def removePolygonOptions(self):
        try:
            self.sides_label.kill()
            self.sides_entry.kill()
            self.size_label.kill()
            self.size_entry.kill()
            self.stroke_num_label.kill()
            self.stroke_entry.kill()
            self.rotation_label.kill()
            self.rotation_entry.kill()
        except:
            pass

    def clearSelection(self):
        self.removeColourOptions()
        self.removeCircleOptions()
        self.removePolygonOptions()

    def clearObjects(self):
        super().clearObjects()
        self.clearSelection()

    def draw_ui(self, window_surface: pygame.surface.Surface):
        if self.selected_index is not None:
            if self.selected_index == "holding":
                obj = self.current_holding_kwargs
                generate = lambda: self.generateHoldingItem()
            else:
                obj = self.current_object["children"][self.selected_index]["visual"]
                generate = lambda: self.setVisualElements()
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_CIRCLE:
                old_radius = obj["radius"]
                try:
                    new_radius = int(self.radius_entry.text)
                    if old_radius != new_radius:
                        obj["radius"] = new_radius
                        generate()
                except:
                    obj["radius"] = old_radius

                old_stroke_width = obj["stroke_width"]
                try:
                    new_stroke_width = float(self.stroke_entry.text)
                    if old_stroke_width != new_stroke_width:
                        obj["stroke_width"] = new_stroke_width
                        generate()
                except:
                    obj["stroke_width"] = old_stroke_width
            if self.mode == self.MODE_NORMAL and self.selected_type == self.SELECTED_POLYGON:
                old_sides = len(obj["verts"])
                old_size = np.linalg.norm(obj["verts"][0], 2)
                cur_rotation = np.arctan2(obj["verts"][0][1], obj["verts"][0][0]) - np.pi / 2
                while cur_rotation < 0:
                    cur_rotation += np.pi
                cur_rotation *= 180 / np.pi
                try:
                    new_sides = int(self.sides_entry.text)
                    new_size = float(self.size_entry.text)
                    new_rot = float(self.rotation_entry.text)
                    assert new_sides > 2
                    if old_sides != new_sides or old_size != new_size or new_rot != cur_rotation:
                        obj["verts"] = [
                            (
                                new_size * np.sin(i * 2 * np.pi / new_sides + new_rot * np.pi / 180),
                                new_size * np.cos(i * 2 * np.pi / new_sides + new_rot * np.pi / 180),
                            )
                            for i in range(new_sides)
                        ]
                    generate()
                except:
                    pass

                old_stroke_width = obj["stroke_width"]
                try:
                    new_stroke_width = float(self.stroke_entry.text)
                    if old_stroke_width != new_stroke_width:
                        obj["stroke_width"] = new_stroke_width
                        generate()
                except:
                    obj["stroke_width"] = old_stroke_width

        ScreenObjectManager.instance.applyToScreen(to_screen=self.bot_screen)
        ScreenObjectManager.instance.screen.blit(self.bot_screen, pygame.Rect(self.side_width - 5, 0, *self.surf_size))
        super().draw_ui(window_surface)

    def changeMode(self, value):
        # Remove/Add dialog components if necessary.
        self.mode = value

    def onPop(self):
        pass
