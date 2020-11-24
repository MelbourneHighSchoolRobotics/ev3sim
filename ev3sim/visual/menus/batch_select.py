import yaml
import os.path
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.visual.menus.base_menu import BaseMenu


class BatchMenu(BaseMenu):
    def sizeObjects(self):
        button_size = self._size[0] / 4, 40
        start_size = self._size[0] / 4, min(self._size[1] / 4, 120)
        start_icon_size = start_size[1] * 0.6, start_size[1] * 0.6
        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        settings_size = (preview_size[0] - 20) * 0.45, preview_size[1] * 0.45
        settings_icon_size = settings_size[1] * 0.6, settings_size[1] * 0.6
        bot_size = preview_size[0] * 0.45, preview_size[1] * 0.45
        bot_icon_size = bot_size[1] * 0.6, bot_size[1] * 0.6
        batch_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].set_dimensions(button_size)
            self.batch_buttons[i].set_position(batch_rect(i))
        self.start_button.set_dimensions(start_size)
        start_button_pos = (self._size[0] * 0.9 - start_size[0], self._size[1] * 0.9 - start_size[1])
        self.start_button.set_position(start_button_pos)
        self.start_icon.set_dimensions(start_icon_size)
        self.start_icon.set_position(
            (
                start_button_pos[0] + start_size[0] / 2 - start_icon_size[0] / 2,
                start_button_pos[1] + start_size[1] * 0.2,
            )
        )
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
        bot_button_pos = (self._size[0] * 0.9 - preview_size[0] + 10, self._size[1] * 0.1 + preview_size[1] + 10)
        self.bot_button.set_dimensions(bot_size)
        self.bot_button.set_position(bot_button_pos)
        self.bot_icon.set_dimensions(bot_icon_size)
        self.bot_icon.set_position(
            (
                bot_button_pos[0] + bot_size[0] / 2 - bot_icon_size[0] / 2,
                bot_button_pos[1] + bot_size[1] * 0.2,
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
        # Find all batch files and show them
        self.available_batches = []
        for rel_dir in ["package", "package/batched_commands/"]:
            actual_dir = find_abs_directory(rel_dir)
            for batch in BatchValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_batches.append((batch[:-5], os.path.join(actual_dir, batch)))
        self.batch_buttons = []
        for i, (show, batch) in enumerate(self.available_batches):
            self.batch_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=dummy_rect,
                    text=show,
                    manager=self,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "batch_select_button"),
                )
            )
        self._all_objs.extend(self.batch_buttons)
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("start-sim"),
        )
        start_icon_path = find_abs("ui/start_sim.png", allowed_areas=["package/assets/"])
        self.start_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(start_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("start-sim-icon"),
        )
        self._all_objs.append(self.start_button)
        self._all_objs.append(self.start_icon)
        self.preview_image = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.Surface(self._size),
            manager=self,
            object_id=pygame_gui.core.ObjectID("preview-image"),
        )
        self._all_objs.append(self.preview_image)
        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("batch-settings"),
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
        self.bot_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("batch-bots"),
        )
        bot_icon_path = find_abs("ui/bot.png", allowed_areas=["package/assets/"])
        self.bot_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(bot_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("bot-icon"),
        )
        self._all_objs.append(self.bot_button)
        self._all_objs.append(self.bot_icon)

    def initWithKwargs(self, **kwargs):
        super().initWithKwargs(**kwargs)
        self.batch_index = -1
        self.start_button.disable()
        self.settings_button.disable()
        self.bot_button.disable()

    def clickStart(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SIM, batch=self.available_batches[self.batch_index][1]
        )

    def clickSettings(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.presets.soccer import visual_settings

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SETTINGS,
            file=self.available_batches[self.batch_index][1],
            settings=visual_settings,
        )
    
    def clickBots(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager
        
        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_BOTS,
            batch_file=self.available_batches[self.batch_index][1],
        )

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("start-sim"):
                self.clickStart()
            elif event.ui_object_id.startswith("batch-settings"):
                self.clickSettings()
            elif event.ui_object_id.startswith("batch-bots"):
                self.clickBots()
            else:
                self.setBatchIndex(int(event.ui_object_id.split("#")[0].split("-")[-1]))
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBatchIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBatchIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickStart()

    def setBatchIndex(self, new_index):
        self.batch_index = new_index
        # Update theming.
        self.start_button.enable()
        self.settings_button.enable()
        self.bot_button.enable()
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].combined_element_ids[1] = (
                "batch_select_button_highlighted" if i == self.batch_index else "batch_select_button"
            )
            self.batch_buttons[i].rebuild_from_changed_theme_data()
        try:
            with open(self.available_batches[self.batch_index][1], "r") as f:
                config = yaml.safe_load(f)
            preset_path = find_abs(
                config["preset_file"], allowed_areas=["local", "local/presets/", "package", "package/presets/"]
            )
            with open(preset_path, "r") as f:
                preset_config = yaml.safe_load(f)
            preset_preview = find_abs(
                preset_config["preview_path"], allowed_areas=["local/assets/", "local", "package/assets/", "package"]
            )
            img = pygame.image.load(preset_preview)
            if img.get_size() != self.preview_image.rect.size:
                img = pygame.transform.smoothscale(img, (self.preview_image.rect.width, self.preview_image.rect.height))
            self.preview_image.set_image(img)
        except:
            pass

    def incrementBatchIndex(self, amount):
        if self.batch_index == -1:
            new_index = amount if amount < 0 else amount - 1
        else:
            new_index = self.batch_index + amount
        new_index %= len(self.batch_buttons)
        self.setBatchIndex(new_index)

    def onPop(self):
        pass
