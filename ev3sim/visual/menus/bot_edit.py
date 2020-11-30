from ev3sim.file_helper import find_abs
import pygame
import pygame_gui
from ev3sim.visual.menus.base_menu import BaseMenu


class BotEditMenu(BaseMenu):
    def initWithKwargs(self, **kwargs):
        self.bot_file = kwargs.get("bot_file", None)
        self.lock_grid = True
        self.grid_size = 5
        super().initWithKwargs(**kwargs)

    def sizeObjects(self):
        # Bg
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        side_width = self._size[0] / 6
        bot_height = self._size[1] / 6
        self.sidebar.set_dimensions((side_width, self._size[1] + 10))
        self.sidebar.set_position((-5, -5))
        self.bot_bar.set_dimensions((self._size[0] - side_width + 20, bot_height))
        self.bot_bar.set_position((-10 + side_width, self._size[1] - bot_height + 5))

        # Clickies
        icon_size = side_width / 2
        self.circle_icon.set_dimensions((icon_size, icon_size))
        self.circle_icon.set_position((side_width / 2 - icon_size / 2, 50))
        self.circle_button.set_dimensions((icon_size, icon_size))
        self.circle_button.set_position((side_width / 2 - icon_size / 2, 50))
        self.polygon_icon.set_dimensions((icon_size, icon_size))
        self.polygon_icon.set_position((side_width / 2 - icon_size / 2, 50 + icon_size * 1.5))
        self.polygon_button.set_dimensions((icon_size, icon_size))
        self.polygon_button.set_position((side_width / 2 - icon_size / 2, 50 + icon_size * 1.5))

        # Other options
        lock_size = side_width / 4
        self.lock_grid_label.set_dimensions(((side_width - 30) - lock_size - 5, lock_size))
        self.lock_grid_label.set_position((10, self._size[1] - lock_size - 60))
        self.lock_grid_image.set_dimensions((lock_size, lock_size))
        self.lock_grid_image.set_position((side_width - lock_size - 20, self._size[1] - lock_size - 60))
        self.lock_grid_button.set_dimensions((lock_size, lock_size))
        self.lock_grid_button.set_position((side_width - lock_size - 20, self._size[1] - lock_size - 60))
        self.updateCheckbox()
        self.grid_size_label.set_dimensions(((side_width - 30) - lock_size - 5, lock_size))
        self.grid_size_label.set_position((10, self._size[1] - lock_size - 15))
        self.grid_size_entry.set_dimensions((lock_size, lock_size))
        self.grid_size_entry.set_position((side_width - lock_size - 20, self._size[1] - lock_size - 15))

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
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("circle-button"):
                self.clickCircle()
            elif event.ui_object_id.startswith("polygon-button"):
                self.clickPolygon()
            elif event.ui_object_id.startswith("lock_grid-button"):
                self.lock_grid = not self.lock_grid
                self.updateCheckbox()

    def onPop(self):
        pass
