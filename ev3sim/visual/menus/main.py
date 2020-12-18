import pygame
import pygame_gui
from ev3sim.file_helper import find_abs
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.settings.main_settings import main_settings
from ev3sim.search_locations import asset_locations, config_locations


class MainMenu(BaseMenu):

    SLIDE_NUMS = 4
    SLIDE_TIME = 5

    def sizeObjects(self):
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        self.title.set_position(((self._size[0] - self.title.rect.width) / 2, 50))
        button_size = self._size[0] / 4, self._size[1] / 8
        self.simulate_button.set_dimensions(button_size)
        self.simulate_button.set_position(
            ((self._size[0] - button_size[0]) / 2, (self._size[1] - button_size[1]) / 2 - button_size[1] * 1.5 + 50)
        )
        self.bot_button.set_dimensions(button_size)
        self.bot_button.set_position(((self._size[0] - button_size[0]) / 2, (self._size[1] - button_size[1]) / 2 + 50))
        self.settings_button.set_dimensions(button_size)
        self.settings_button.set_position(
            ((self._size[0] - button_size[0]) / 2, (self._size[1] - button_size[1]) / 2 + button_size[1] * 1.5 + 50)
        )

    def generateObjects(self):
        from ev3sim.visual.manager import ScreenObjectManager

        self.slide_index = 0
        self.swapSlides()
        dummy_rect = pygame.Rect(0, 0, *self._size)
        # In order to respect theme changes, objects must be built in initWithKwargs
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)
        self.title = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(0, 0, -1, -1),
            html_text="EV3<i>Sim</i>",
            manager=self,
            object_id=pygame_gui.core.ObjectID("title"),
        )
        self._all_objs.append(self.title)
        self.simulate_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="Simulate",
            manager=self,
            object_id=pygame_gui.core.ObjectID("simulate_button", "menu_button"),
        )
        self.addButtonEvent(
            "simulate_button", lambda: ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BATCH)
        )
        self._all_objs.append(self.simulate_button)
        self.bot_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="Bots",
            manager=self,
            object_id=pygame_gui.core.ObjectID("bots_button", "menu_button"),
        )
        self.addButtonEvent(
            "bots_button", lambda: ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BOTS)
        )
        self._all_objs.append(self.bot_button)
        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="Settings",
            manager=self,
            object_id=pygame_gui.core.ObjectID("main_settings_button", "menu_button"),
        )

        def clickSettings():
            ScreenObjectManager.instance.pushScreen(
                ScreenObjectManager.SCREEN_SETTINGS,
                file=find_abs("user_config.yaml", config_locations()),
                settings=main_settings,
            )
            ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].clearEvents()

        self.addButtonEvent("main_settings_button", clickSettings)
        self._all_objs.append(self.settings_button)

    def swapSlides(self):
        self.remaining = 0
        self.slide_index += 1
        self.slide_index %= self.SLIDE_NUMS
        self.slide_surface_prev = pygame.image.load(
            find_abs(f"bg_slide{(self.slide_index - 1) % self.SLIDE_NUMS}.png", asset_locations())
        )
        self.slide_surface_next = pygame.image.load(find_abs(f"bg_slide{self.slide_index}.png", asset_locations()))

    MAX_ALPHA = 0.4
    FADE_PCT = 0.55

    def update(self, time_delta: float):
        super().update(time_delta)
        self.remaining += time_delta
        if self.remaining >= self.SLIDE_TIME:
            self.swapSlides()
        bg_image = pygame.Surface(self._size, depth=32)
        bg_image.fill(pygame.Color(16, 16, 16))
        prop_time = self.remaining / self.SLIDE_TIME
        alpha_prev = int(
            (self.FADE_PCT - prop_time) / self.FADE_PCT * 255 * self.MAX_ALPHA if prop_time < self.FADE_PCT else 0
        )
        alpha_next = int(
            (prop_time - (1 - self.FADE_PCT)) / self.FADE_PCT * 255 * self.MAX_ALPHA if prop_time > 0.25 else 0
        )
        img_prev = self.slide_surface_prev
        img_next = self.slide_surface_next
        img_prev.set_alpha(alpha_prev)
        img_next.set_alpha(alpha_next)
        bg_image.blit(img_prev, pygame.Rect(0, 0, *self._size))
        bg_image.blit(img_next, pygame.Rect(0, 0, *self._size))
        self.bg.set_image(bg_image)

    def draw_ui(self, window_surface: pygame.surface.Surface):
        super().draw_ui(window_surface)

    def onPop(self):
        pass
