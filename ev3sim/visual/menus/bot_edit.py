import pygame
import pygame_gui
import yaml
import numpy as np
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.visual.utils import screenspace_to_worldspace
from ev3sim.file_helper import find_abs


class BotEditMenu(BaseMenu):

    MODE_DIALOG_DEVICE = "DEVICE_SELECT"
    MODE_NORMAL = "NORMAL"

    def initWithKwargs(self, **kwargs):
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
        self.setVisualElements([self.current_object])

    def setVisualElements(self, elements):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.startUp()
        ScreenObjectManager.instance.resetVisualElements()
        mSize = min(*self.surf_size)
        elems = ScriptLoader.instance.loadElements(elements, preview_mode=True)
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

    def sizeObjects(self):
        # Bg
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
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
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)
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

    def clickSelect(self):
        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")
        self.current_holding = None

    def clickCircle(self):
        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")
        from ev3sim.visual.objects import visualFactory

        self.current_holding_kwargs = {
            "type": "visual",
            "name": "Circle",
            "radius": 1,
            "fill": "#878E88",
            "stroke_width": 0.1,
            "stroke": "#ffffff",
            "zPos": 5,
        }
        self.current_holding = visualFactory(**self.current_holding_kwargs)
        self.current_holding.customMap = self.customMap
        ScreenObjectManager.instance.registerVisual(self.current_holding, "holding")

    def clickPolygon(self):
        if "holding" in ScreenObjectManager.instance.objects:
            ScreenObjectManager.instance.unregisterVisual("holding")
        from ev3sim.visual.objects import visualFactory

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
        self.current_holding = visualFactory(**self.current_holding_kwargs)
        self.current_holding.customMap = self.customMap
        ScreenObjectManager.instance.registerVisual(self.current_holding, "holding")

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
            if event.type == pygame.MOUSEMOTION:
                if self.current_holding is not None:
                    self.current_holding.position = screenspace_to_worldspace(
                        (event.pos[0] - self.side_width, event.pos[1]), customScreen=self.customMap
                    )

    def draw_ui(self, window_surface: pygame.surface.Surface):
        super().draw_ui(window_surface)
        ScreenObjectManager.instance.applyToScreen(to_screen=self.bot_screen)
        ScreenObjectManager.instance.screen.blit(self.bot_screen, pygame.Rect(self.side_width - 5, 0, *self.surf_size))

    def changeMode(self, value):
        # Remove/Add dialog components if necessary.
        self.mode = value

    def onPop(self):
        pass
