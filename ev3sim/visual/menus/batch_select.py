from ev3sim.visual.menus.utils import CustomScroll
import yaml
import os
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.search_locations import asset_locations, batch_locations, bot_locations, preset_locations


class BatchMenu(BaseMenu):

    bot_list = []

    def sizeObjects(self):
        button_size = self._size[0] / 4, 60
        info_size = self._size[0] / 4 - 20, 15
        new_size = self._size[0] / 8, min(self._size[1] / 6, 90)
        new_icon_size = new_size[1] * 0.6, new_size[1] * 0.6
        start_size = self._size[0] / 4, min(self._size[1] / 4, 120)
        start_icon_size = start_size[1] * 0.6, start_size[1] * 0.6
        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        settings_size = preview_size[0] * 0.45, preview_size[1] * 0.45
        settings_icon_size = settings_size[1] * 0.6, settings_size[1] * 0.6
        bot_size = preview_size[0] * 0.45, preview_size[1] * 0.45
        bot_icon_size = bot_size[1] * 0.6, bot_size[1] * 0.6
        batch_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        info_rect = lambda b_r: (
            b_r[0] + button_size[0] - info_size[0] - 10,
            b_r[1] + button_size[1] - info_size[1] - 5,
        )
        size = (self._size[0] / 4 + self._size[0] / 10, self._size[1] * 0.9 - new_size[1])
        # Setting dimensions and positions on a UIScrollingContainer seems buggy. This works.
        self.scrolling_container.set_dimensions(size)
        self.scrolling_container.set_position(size)
        self.bg.set_dimensions(self._size)
        self.bg.set_position((0, 0))
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].set_dimensions(button_size)
            self.batch_buttons[i].set_position(batch_rect(i))
            self.batch_descriptions[i].set_dimensions(info_size)
            self.batch_descriptions[i].set_position(info_rect(batch_rect(i)))
        self.new_batch.set_dimensions(new_size)
        new_batch_pos = (batch_rect(0)[0] + button_size[0] - new_size[0], self._size[1] * 0.9 - new_size[1])
        self.new_batch.set_position(new_batch_pos)
        self.new_icon.set_dimensions(new_icon_size)
        self.new_icon.set_position(
            (
                new_batch_pos[0] + new_size[0] / 2 - new_icon_size[0] / 2,
                new_batch_pos[1] + new_size[1] * 0.2,
            )
        )
        self.remove_batch.set_dimensions(new_size)
        remove_batch_pos = (batch_rect(0)[0], self._size[1] * 0.9 - new_size[1])
        self.remove_batch.set_position(remove_batch_pos)
        self.remove_icon.set_dimensions(new_icon_size)
        self.remove_icon.set_position(
            (
                remove_batch_pos[0] + new_size[0] / 2 - new_icon_size[0] / 2,
                remove_batch_pos[1] + new_size[1] * 0.2,
            )
        )
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
        settings_button_pos = (self._size[0] * 0.9 - settings_size[0] - preview_size[0] - 10, self._size[1] * 0.1)
        self.settings_button.set_dimensions(settings_size)
        self.settings_button.set_position(settings_button_pos)
        self.settings_icon.set_dimensions(settings_icon_size)
        self.settings_icon.set_position(
            (
                settings_button_pos[0] + settings_size[0] / 2 - settings_icon_size[0] / 2,
                settings_button_pos[1] + settings_size[1] * 0.2,
            )
        )
        bot_button_pos = (
            self._size[0] * 0.9 - preview_size[0] - bot_size[0] - 10,
            self._size[1] * 0.1 + preview_size[1] / 2 + 10,
        )
        self.bot_button.set_dimensions(bot_size)
        self.bot_button.set_position(bot_button_pos)
        self.bot_icon.set_dimensions(bot_icon_size)
        self.bot_icon.set_position(
            (
                bot_button_pos[0] + bot_size[0] / 2 - bot_icon_size[0] / 2,
                bot_button_pos[1] + bot_size[1] * 0.2,
            )
        )

        n_bot_spots = len(self.bot_list)
        if n_bot_spots > 0:
            for i in range(n_bot_spots):
                self.sizeBotImage(i, big_mode=n_bot_spots < 1)

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
        for rel_dir in batch_locations:
            try:
                actual_dir = find_abs_directory(rel_dir)
            except:
                continue
            for batch in BatchValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_batches.append((batch[:-5], os.path.join(actual_dir, batch), rel_dir, batch))
        self.batch_buttons = []
        self.batch_descriptions = []

        self.scrolling_container = CustomScroll(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("scroll_container"),
        )
        self.scrolling_container.num_elems = len(self.available_batches)
        for i, (show, batch, rel_dir, filename) in enumerate(self.available_batches):
            self.batch_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=dummy_rect,
                    text=show,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "list_button"),
                )
            )
            self.batch_descriptions.append(
                pygame_gui.elements.UILabel(
                    relative_rect=dummy_rect,
                    text=rel_dir,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(show + "-dir-" + str(i), "button_info"),
                )
            )
        self._all_objs.extend(self.batch_buttons)
        self._all_objs.extend(self.batch_descriptions)
        self.new_batch = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("new_batch", "action_button"),
        )
        new_batch_path = find_abs("ui/add.png", allowed_areas=asset_locations)
        self.new_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(new_batch_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("new_batch-icon"),
        )
        self._all_objs.append(self.new_batch)
        self._all_objs.append(self.new_icon)
        self.remove_batch = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_batch", "cancel-changes"),
        )
        remove_batch_path = find_abs("ui/bin.png", allowed_areas=asset_locations)
        self.remove_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(remove_batch_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_batch-icon"),
        )
        self._all_objs.append(self.remove_batch)
        self._all_objs.append(self.remove_icon)
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("start-sim", "action_button"),
        )
        start_icon_path = find_abs("ui/start_sim.png", allowed_areas=asset_locations)
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
            object_id=pygame_gui.core.ObjectID("batch-settings", "settings_buttons"),
        )
        settings_icon_path = find_abs("ui/settings.png", allowed_areas=asset_locations)
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
            object_id=pygame_gui.core.ObjectID("batch-bots", "settings_buttons"),
        )
        bot_icon_path = find_abs("ui/bot.png", allowed_areas=asset_locations)
        self.bot_icon = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=pygame.image.load(bot_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("bot-icon"),
        )
        self._all_objs.append(self.bot_button)
        self._all_objs.append(self.bot_icon)
        n_bot_spots = len(self.bot_list)
        if n_bot_spots > 0:
            self.bot_loc_spots = []
            for i in range(n_bot_spots):
                self.bot_loc_spots.append(self.createBotImage(i))
            self._all_objs.extend(self.bot_loc_spots)

    def initWithKwargs(self, **kwargs):
        super().initWithKwargs(**kwargs)
        self.batch_index = -1
        self.start_button.disable()
        self.settings_button.disable()
        self.remove_batch.disable()
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
            allows_filename_change=not self.available_batches[self.batch_index][2].startswith("package"),
        )

        def onSave(filename):
            self.clearObjects()
            self.generateObjects()
            self.sizeObjects()

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].onSave = onSave

    def clickNew(self):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.presets.soccer import visual_settings

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SETTINGS,
            settings=visual_settings,
            creating=True,
            creation_area="workspace/batched_commands/",
            starting_data={
                "preset_file": "soccer.yaml",
                "bots": [],
                "settings": {
                    "soccer": {},
                },
            },
        )

        def onSave(filename):
            self.clearObjects()
            self.generateObjects()
            self.sizeObjects()

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].onSave = onSave

    def clickBots(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_BOTS,
            batch_file=self.available_batches[self.batch_index][1],
        )

    def clickRemove(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        os.remove(self.available_batches[self.batch_index][1])
        self.batch_index = -1
        self.clearObjects()
        self.generateObjects()
        self.sizeObjects()

    def createBotImage(self, index):

        fname = find_abs(self.bot_list[index], bot_locations)
        with open(fname, "r") as f:
            config = yaml.safe_load(f)
        bot_preview = find_abs(config["preview_path"], allowed_areas=asset_locations)
        img = pygame.image.load(bot_preview)
        img = pygame.transform.smoothscale(img, self._size)
        return pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(0, 0, *self._size),
            image_surface=img,
            manager=self,
            object_id=pygame_gui.core.ObjectID(f"bot-image-{self.bot_list[index]}"),
        )

    def sizeBotImage(self, index, big_mode=False):
        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        if big_mode:
            # beeg
            self.bot_loc_spots[index].set_dimensions((preview_size[0], preview_size[0]))
            self.bot_loc_spots[index].set_position(
                (
                    self._size[0] * 0.9 - preview_size[0],
                    self._size[1] * 0.1 + preview_size[1] + 20 + (preview_size[0] * 1.1) * index,
                )
            )
        else:
            self.bot_loc_spots[index].set_dimensions((preview_size[0] * 0.45, preview_size[0] * 0.45))
            self.bot_loc_spots[index].set_position(
                (
                    self._size[0] * 0.9 - preview_size[0] * (1 if index % 2 == 0 else 0.45),
                    self._size[1] * 0.1 + preview_size[1] + 20 + (index // 2) * preview_size[0] * 0.55,
                )
            )

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("start-sim"):
                self.clickStart()
            elif event.ui_object_id.startswith("batch-settings"):
                self.clickSettings()
            elif event.ui_object_id.startswith("batch-bots"):
                self.clickBots()
            elif event.ui_object_id.startswith("new_batch"):
                self.clickNew()
            elif event.ui_object_id.startswith("remove_batch"):
                self.clickRemove()
            else:
                if event.ui_object_id.split("#")[0].split("-")[-1].isnumeric():
                    self.setBatchIndex(int(event.ui_object_id.split("#")[0].split("-")[-1]))
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBatchIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBatchIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickStart()
            elif event.key == pygame.K_n:
                self.clickNew()

    def setBatchIndex(self, new_index):
        self.batch_index = new_index
        with open(self.available_batches[self.batch_index][1], "r") as f:
            config = yaml.safe_load(f)
        # Trigger regeneration
        bots = config["bots"]
        self.bot_list = bots
        self.clearObjects()
        self.generateObjects()
        self.sizeObjects()
        # Update theming.
        self.start_button.enable()
        self.settings_button.enable()
        if self.available_batches[self.batch_index][2].startswith("package"):
            self.remove_batch.disable()
        else:
            self.remove_batch.enable()
        self.bot_button.enable()
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].combined_element_ids[2] = (
                "list_button_highlighted" if i == self.batch_index else "list_button"
            )
            self.batch_buttons[i].rebuild_from_changed_theme_data()
            self.batch_descriptions[i].combined_element_ids[2] = (
                "button_info_selected" if i == self.batch_index else "button_info"
            )
            self.batch_descriptions[i].rebuild_from_changed_theme_data()
        preset_path = find_abs(config["preset_file"], allowed_areas=preset_locations)
        with open(preset_path, "r") as f:
            preset_config = yaml.safe_load(f)
        preset_preview = find_abs(preset_config["preview_path"], allowed_areas=asset_locations)
        img = pygame.image.load(preset_preview)
        if img.get_size() != self.preview_image.rect.size:
            img = pygame.transform.smoothscale(img, (self.preview_image.rect.width, self.preview_image.rect.height))
        self.preview_image.set_image(img)

    def incrementBatchIndex(self, amount):
        if self.batch_index == -1:
            new_index = amount if amount < 0 else amount - 1
        else:
            new_index = self.batch_index + amount
        new_index %= len(self.batch_buttons)
        self.setBatchIndex(new_index)

    def resetVisual(self):
        self.start_button.disable()
        self.settings_button.disable()
        self.remove_batch.disable()
        self.bot_button.disable()
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].combined_element_ids[2] = "list_button"
            self.batch_buttons[i].rebuild_from_changed_theme_data()
            self.batch_descriptions[i].combined_element_ids[2] = "button_info"
            self.batch_descriptions[i].rebuild_from_changed_theme_data()

    def onPop(self):
        self.bot_index = -1
        self.resetVisual()
