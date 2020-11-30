from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.file_helper import find_abs
import pygame
import pygame_gui
from ev3sim.visual.menus.base_menu import BaseMenu


class BotEditMenu(BaseMenu):

    MODE_DIALOG_DEVICE = "DEVICE_SELECT"
    MODE_NORMAL = "NORMAL"

    def initWithKwargs(self, **kwargs):
        self.bot_file = kwargs.get("bot_file", None)
        self.lock_grid = True
        self.grid_size = 5
        self.mode = self.MODE_NORMAL
        self.current_object = {
            "physics": True,
            "type": "object",
            "visual": {
                "name": "Circle",
                "radius": 8.5,
                "fill": "#878E88",
                "stroke_width": 0.1,
                "stroke": "#ffffff",
                "zPos": 2,
            },
            "collider": "inherit",
            "mass": 5,
            "restitution": 0.2,
            "friction": 0.8,
            "children": [],
            "key": "phys_obj",
        }
        self.current_holding = None
        super().initWithKwargs(**kwargs)
        self.setVisualElements([self.current_object])

    def setVisualElements(self, elements):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.startUp()
        ScreenObjectManager.instance.resetVisualElements()
        ScriptLoader.instance.loadElements(elements, preview_mode=True)

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

    def clickCircle(self):
        print("Circle!")

    def clickPolygon(self):
        print("Polygon!")

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
                if event.ui_object_id.startswith("circle-button"):
                    self.clickCircle()
                elif event.ui_object_id.startswith("polygon-button"):
                    self.clickPolygon()
                elif event.ui_object_id.startswith("lock_grid-button"):
                    self.lock_grid = not self.lock_grid
                    self.updateCheckbox()

    def draw_ui(self, window_surface: pygame.surface.Surface):
        super().draw_ui(window_surface)
        surf_size = (self._size[0] - self.side_width + 5, self._size[1] - self.bot_height + 5)
        bot_screen = pygame.Surface(surf_size)
        ScreenObjectManager.instance.applyToScreen(to_screen=bot_screen)
        ScreenObjectManager.instance.screen.blit(bot_screen, pygame.Rect(self.side_width - 5, 0, *surf_size))

    def changeMode(self, value):
        # Remove/Add dialog components if necessary.
        self.mode = value

    def onPop(self):
        pass
