import yaml
import os.path
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.bot_files import BotValidator
from ev3sim.visual.menus.base_menu import BaseMenu


class BotMenu(BaseMenu):
    def sizeObjects(self):
        button_size = self._size[0] / 4, 40
        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        settings_size = preview_size[0] * 0.4, preview_size[1] * 0.4
        settings_icon_size = settings_size[1] * 0.6, settings_size[1] * 0.6
        bot_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        for i in range(len(self.bot_buttons)):
            self.bot_buttons[i].set_dimensions(button_size)
            self.bot_buttons[i].set_position(bot_rect(i))
        self.preview_image.set_dimensions(preview_size)
        self.preview_image.set_position((self._size[0] * 0.9 - preview_size[0], self._size[1] * 0.1))
        settings_button_pos = (self._size[0] * 0.9 - settings_size[0] - 10, self._size[1] * 0.1 + preview_size[1] + 10)
        self.settings_button.set_dimensions(settings_size)
        self.settings_button.set_position(settings_button_pos)
        self.settings_icon.set_dimensions(settings_icon_size)
        self.settings_icon.set_position(
            (
                settings_button_pos[0] + settings_size[0] / 2 - settings_icon_size[0] / 2,
                settings_button_pos[1] + settings_size[1] * 0.2,
            )
        )

    def generateObjects(self):
        dummy_rect = pygame.Rect(0, 0, *self._size)
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)
        # Find all bot files and show them
        self.available_bots = []
        for rel_dir in ["package", "package/robots/"]:
            actual_dir = find_abs_directory(rel_dir)
            for bot in BotValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_bots.append((bot[:-5], os.path.join(actual_dir, bot)))
        self.bot_buttons = []
        for i, (show, bot) in enumerate(self.available_bots):
            self.bot_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=dummy_rect,
                    text=show,
                    manager=self,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "bot_select_button"),
                )
            )
        self._all_objs.extend(self.bot_buttons)
        image = pygame.Surface(self._size)
        image.fill(pygame.Color(self.bg.background_colour))
        self.preview_image = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=image,
            manager=self,
            object_id=pygame_gui.core.ObjectID("preview-image"),
        )
        self._all_objs.append(self.preview_image)
        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("bot-settings"),
        )
        settings_icon_path = find_abs("ui/settings.png", allowed_areas=["package/assets/"])
        self.settings_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(settings_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("settings-icon"),
        )
        self._all_objs.append(self.settings_button)
        self._all_objs.append(self.settings_icon)

    def initWithKwargs(self, **kwargs):
        super().initWithKwargs(**kwargs)
        self.bot_index = -1
        self.settings_button.disable()

    def clickSettings(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.captureBotImage(
            self.available_bots[self.bot_index][1], bg=pygame.Color(self.bg.background_colour)
        )
        self.blitCurrentBotPreview()

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("bot-settings"):
                self.clickSettings()
            else:
                self.setBotIndex(int(event.ui_object_id.split("#")[0].split("-")[-1]))
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBotIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBotIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickStart()

    def setBotIndex(self, new_index):
        self.bot_index = new_index
        self.settings_button.enable()
        for i in range(len(self.bot_buttons)):
            self.bot_buttons[i].combined_element_ids[1] = (
                "bot_select_button_highlighted" if i == self.bot_index else "bot_select_button"
            )
            self.bot_buttons[i].rebuild_from_changed_theme_data()
        try:
            self.blitCurrentBotPreview()
        except Exception as e:
            raise e

    def blitCurrentBotPreview(self):
        with open(self.available_bots[self.bot_index][1], "r") as f:
            config = yaml.safe_load(f)
        bot_preview = find_abs(
            config["preview_path"], allowed_areas=["local/assets/", "local", "package/assets/", "package"]
        )
        img = pygame.image.load(bot_preview)
        if img.get_size() != self.preview_image.rect.size:
            img = pygame.transform.smoothscale(img, (self.preview_image.rect.width, self.preview_image.rect.height))
        self.preview_image.set_image(img)

    def incrementBotIndex(self, amount):
        if self.bot_index == -1:
            new_index = amount if amount < 0 else amount - 1
        else:
            new_index = self.bot_index + amount
        new_index %= len(self.bot_buttons)
        self.setBotIndex(new_index)

    def onPop(self):
        pass
