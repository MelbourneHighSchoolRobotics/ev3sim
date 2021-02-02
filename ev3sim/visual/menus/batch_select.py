from ev3sim.visual.menus.utils import CustomScroll
import yaml
import os
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.validation.preset_files import PresetValidator
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.search_locations import asset_locations, batch_locations, bot_locations, preset_locations


class BatchMenu(BaseMenu):

    MODE_NORMAL = "NORMAL"
    MODE_BATCH = "BATCH_SELECTION"
    bot_list = []

    def iconPos(self, buttonPos, buttonSize, iconSize):
        return (
            buttonPos[0] + buttonSize[0] / 2 - iconSize[0] / 2,
            buttonPos[1] + buttonSize[1] * 0.2,
        )

    def generateObjects(self):
        # First, find all batch files.
        self.available_batches = []
        for rel_dir in batch_locations():
            try:
                actual_dir = find_abs_directory(rel_dir)
            except:
                continue
            for batch in BatchValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .sim
                with open(os.path.join(actual_dir, batch), "r") as f:
                    config = yaml.safe_load(f)
                with open(find_abs(config["preset_file"], preset_locations()), "r") as f:
                    preset = yaml.safe_load(f)
                if not config.get("hidden", False):
                    self.available_batches.append(
                        (batch[:-4], os.path.join(actual_dir, batch), rel_dir, batch, preset["button_bg"])
                    )

        for i, bot in enumerate(self.available_batches):
            if i == self.batch_index:
                with open(bot[1], "r") as f:
                    config = yaml.safe_load(f)
                # Update bot information
                bots = config["bots"]
                self.bot_list = bots
                preset_path = find_abs(config["preset_file"], allowed_areas=preset_locations())
                with open(preset_path, "r") as f:
                    preset_config = yaml.safe_load(f)
                preset_preview = find_abs(preset_config["preview_path"], allowed_areas=asset_locations())
                self.preview_image_source = pygame.image.load(preset_preview)

        # Draw Background
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, *self._size),
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)

        # Scrolling container
        old_y = getattr(getattr(self, "scrolling_container", None), "cur_y", 0)
        self.scrolling_container = CustomScroll(
            relative_rect=pygame.Rect(0, 0, self._size[0], 5 * self._size[1]),
            manager=self,
            object_id=pygame_gui.core.ObjectID("scroll_container"),
        )
        picture_width = 360
        self.scrolling_container.elems_size = picture_width * 0.4
        self.scrolling_container.span_elems = 4
        self.scrolling_container.num_elems = len(self.available_batches)
        scrolling_size = (self._size[0] / 4 + self._size[0] / 5, self._size[1] * 0.95 - min(self._size[1] / 6, 90) + 20)
        # Setting dimensions and positions on a UIScrollingContainer seems buggy. This works.
        self.scrolling_container.set_dimensions(scrolling_size)
        self.scrolling_container.set_position(scrolling_size)
        self.scrolling_container.cur_y = old_y
        self.scrolling_container.set_scroll(old_y)
        self._all_objs.append(self.scrolling_container)

        # The batch buttons
        batch_rect = lambda i: (0, self._size[1] / 20 + i * picture_width * 0.4)
        self.batch_bgs = []
        self.batch_buttons = []
        self.batch_titles = []
        self.batch_descriptions = []
        self.batch_fgs = []
        for i, (show, batch, rel_dir, filename, preset_bg_path) in enumerate(self.available_batches):
            bg_img = pygame.image.load(find_abs(preset_bg_path, asset_locations()))
            self.batch_bgs.append(
                pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(0, batch_rect(i)[1], picture_width, picture_width * 0.33),
                    image_surface=bg_img,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(),
                )
            )
            self.batch_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(0, batch_rect(i)[1], picture_width * 0.68, picture_width * 0.2),
                    text="",
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(f"button-{i}", "list_button"),
                )
            )
            self.addButtonEvent(f"button-{i}", self.setBatchIndex, i)
            self.batch_titles.append(
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(12, batch_rect(i)[1] + 5, picture_width, picture_width * 0.2),
                    text=show,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(f"button-{i}-label", "button_text"),
                )
            )
            self.batch_titles[-1].set_dimensions(self.batch_titles[-1].font.size(self.batch_titles[-1].text))
            self.batch_descriptions.append(
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(0, batch_rect(i)[1], picture_width, picture_width * 0.2 - 20),
                    text=rel_dir,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(f"button-{i}-info", "button_info"),
                )
            )
            size = self.batch_descriptions[-1].font.size(self.batch_descriptions[-1].text)
            self.batch_descriptions[-1].set_position(
                (picture_width * 0.68 - size[0] - 10, batch_rect(i)[1] + picture_width * 0.2 - size[1] - 10)
            )
            self.batch_descriptions[-1].set_dimensions(size)
            fg_img = pygame.image.load(find_abs("ui/button_fg.png", asset_locations()))
            self.batch_fgs.append(
                pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(0, batch_rect(i)[1], picture_width, picture_width * 0.33),
                    image_surface=fg_img,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(f"button-{i}-fg", "button-fg"),
                )
            )
        self._all_objs.extend(self.batch_bgs)
        self._all_objs.extend(self.batch_buttons)
        self._all_objs.extend(self.batch_titles)
        self._all_objs.extend(self.batch_descriptions)
        self._all_objs.extend(self.batch_fgs)

        # New + Remove
        new_size = self._size[0] / 8, min(self._size[1] / 6, 90)
        new_icon_size = new_size[1] * 0.6, new_size[1] * 0.6
        new_batch_pos = (self._size[0] / 3 - new_size[0], self._size[1] * 0.95 - new_size[1])
        self.new_batch = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*new_batch_pos, *new_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("new_batch", "action_button"),
        )
        self.addButtonEvent("new_batch", self.addBatchDialog)
        new_batch_path = find_abs("ui/add.png", allowed_areas=asset_locations())
        self.new_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(new_batch_pos, new_size, new_icon_size), *new_icon_size),
            image_surface=pygame.image.load(new_batch_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("new_batch-icon"),
        )
        self._all_objs.append(self.new_batch)
        self._all_objs.append(self.new_icon)

        remove_batch_pos = (self._size[0] / 3 - 2 * new_size[0] - 15, self._size[1] * 0.95 - new_size[1])
        self.remove_batch = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*remove_batch_pos, *new_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_batch", "cancel-changes"),
        )
        self.addButtonEvent("remove_batch", self.clickRemove)
        if not self.remove_enable:
            self.remove_batch.disable()
        remove_batch_path = find_abs("ui/bin.png", allowed_areas=asset_locations())
        self.remove_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(remove_batch_pos, new_size, new_icon_size), *new_icon_size),
            image_surface=pygame.image.load(remove_batch_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_batch-icon"),
        )
        self._all_objs.append(self.remove_batch)
        self._all_objs.append(self.remove_icon)

        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        preview_image_pos = (self._size[0] * 0.9 - preview_size[0], self._size[1] * 0.1)
        self.preview_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*preview_image_pos, *preview_size),
            image_surface=pygame.Surface(self._size),
            manager=self,
            object_id=pygame_gui.core.ObjectID("preview-image"),
        )
        self._all_objs.append(self.preview_image)

        start_size = self._size[0] / 4, min(self._size[1] / 4, 120)
        start_icon_size = start_size[1] * 0.6, start_size[1] * 0.6
        start_button_pos = (self._size[0] * 0.9 - start_size[0], self._size[1] * 0.9 - start_size[1])
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*start_button_pos, *start_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("start-sim", "action_button"),
        )
        self.addButtonEvent("start-sim", self.clickStart)
        if not self.start_enable:
            self.start_button.disable()
        start_icon_path = find_abs("ui/start_sim.png", allowed_areas=asset_locations())
        self.start_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(start_button_pos, start_size, start_icon_size), *start_icon_size),
            image_surface=pygame.image.load(start_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("start-sim-icon"),
        )
        self._all_objs.append(self.start_button)
        self._all_objs.append(self.start_icon)

        settings_size = preview_size[0] * 0.45, preview_size[1] * 0.45
        settings_icon_size = settings_size[1] * 0.6, settings_size[1] * 0.6
        settings_button_pos = (self._size[0] * 0.9 - settings_size[0] - preview_size[0] - 10, self._size[1] * 0.1)
        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*settings_button_pos, *settings_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("batch-settings", "settings_buttons"),
        )
        self.addButtonEvent("batch-settings", self.clickSettings)
        if not self.settings_enable:
            self.settings_button.disable()
        settings_icon_path = find_abs("ui/settings.png", allowed_areas=asset_locations())
        self.settings_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(
                *self.iconPos(settings_button_pos, settings_size, settings_icon_size), *settings_icon_size
            ),
            image_surface=pygame.image.load(settings_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("settings-icon"),
        )
        self._all_objs.append(self.settings_button)
        self._all_objs.append(self.settings_icon)

        bot_size = preview_size[0] * 0.45, preview_size[1] * 0.45
        bot_icon_size = bot_size[1] * 0.6, bot_size[1] * 0.6
        bot_button_pos = (
            self._size[0] * 0.9 - preview_size[0] - bot_size[0] - 10,
            self._size[1] * 0.1 + preview_size[1] / 2 + 10,
        )
        self.bot_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*bot_button_pos, *bot_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("batch-bots", "settings_buttons"),
        )
        self.addButtonEvent("batch-bots", self.clickBots)
        if not self.bot_enable:
            self.bot_button.disable()
        bot_icon_path = find_abs("ui/bot.png", allowed_areas=asset_locations())
        self.bot_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(bot_button_pos, bot_size, bot_icon_size), *bot_icon_size),
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
                self.sizeBotImage(i, big_mode=n_bot_spots < 1)
            self._all_objs.extend(self.bot_loc_spots)

        if self.mode == self.MODE_BATCH:
            self.generateBatchPicker()

        self.changeSelectedTheming()
        super().generateObjects()

    def generateBatchPicker(self):
        class BatchPicker(pygame_gui.elements.UIWindow):
            def kill(self2):
                super().kill()
                self.mode = self.MODE_NORMAL
                self.regenerateObjects()

            def process_event(self2, event: pygame.event.Event) -> bool:
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_object_id.split(".")[-1].startswith("preset-"):
                        preset_index = int(event.ui_object_id.split(".")[-1].split("-")[1])
                        self.generateBatch(preset_index)
                        self2.kill()
                return super().process_event(event)

        picker_size = (self._size[0] * 0.7, self._size[1] * 0.7)
        self.picker = BatchPicker(
            rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *picker_size),
            manager=self,
            window_display_title="Pick Batch Type",
            object_id=pygame_gui.core.ObjectID("batch_dialog"),
        )

        label_height = (self.picker.rect.height - 60) / 3
        image_height = 2 * (self.picker.rect.height - 60) / 3 - 60

        self.preset_images = []
        self.preset_labels = []
        self.preset_buttons = []
        self.available_presets = []
        for rel_dir in preset_locations():
            try:
                actual_dir = find_abs_directory(rel_dir)
            except:
                continue
            for preset in PresetValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                with open(os.path.join(actual_dir, preset), "r") as f:
                    config = yaml.safe_load(f)
                if not config.get("hidden", False):
                    self.available_presets.append(
                        (preset[:-5], os.path.join(actual_dir, preset), rel_dir, preset, config)
                    )
        for i, preset_type in enumerate(self.available_presets):
            self.preset_images.append(
                pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(
                        40 + (i % 2) * ((self.picker.rect.width - 90) / 2 + 20),
                        40 + label_height,
                        (self.picker.rect.width - 90) / 2 - 40,
                        image_height,
                    ),
                    image_surface=pygame.image.load(find_abs(preset_type[4]["preview_path"], asset_locations())),
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"preset-{i}-image"),
                )
            )
            self.preset_labels.append(
                pygame_gui.elements.UITextBox(
                    relative_rect=pygame.Rect(
                        20 + (i % 2) * (self.picker.rect.width - 60) / 2,
                        20,
                        (self.picker.rect.width - 60) / 2,
                        label_height,
                    ),
                    html_text=preset_type[4].get("preset_description", ""),
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"preset-{i}-label", "text_dialog"),
                )
            )
            self.preset_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(
                        20 + (i % 2) * (self.picker.rect.width - 60) / 2,
                        20,
                        (self.picker.rect.width - 60) / 2,
                        self.picker.rect.height - 40,
                    ),
                    text="",
                    manager=self,
                    container=self.picker,
                    object_id=pygame_gui.core.ObjectID(f"preset-{i}-button", "invis_button"),
                )
            )

            def clickPreset(i):
                self.mode = self.MODE_NORMAL
                self.generateBatch(i)
                self.regenerateObjects()

            self.addButtonEvent(f"preset-{i}-button", clickPreset, i)
        self._all_objs.extend(self.preset_images)
        self._all_objs.extend(self.preset_labels)
        self._all_objs.extend(self.preset_buttons)

    def changeSelectedTheming(self):
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].combined_element_ids[1] = (
                "list_button_highlighted" if i == self.batch_index else "list_button"
            )
            self.batch_buttons[i].rebuild_from_changed_theme_data()
            self.batch_titles[i].combined_element_ids[1] = (
                "button_text_highlighted" if i == self.batch_index else "button_text"
            )
            self.batch_titles[i].rebuild_from_changed_theme_data()
            self.batch_descriptions[i].combined_element_ids[1] = (
                "button_info_highlighted" if i == self.batch_index else "button_info"
            )
            self.batch_descriptions[i].rebuild_from_changed_theme_data()
        if self.batch_index != -1:
            if self.preview_image_source.get_size() != self.preview_image.rect.size:
                self.preview_image_source = pygame.transform.smoothscale(
                    self.preview_image_source, (self.preview_image.rect.width, self.preview_image.rect.height)
                )
            self.preview_image.set_image(self.preview_image_source)

    def initWithKwargs(self, **kwargs):
        self.mode = self.MODE_NORMAL
        self.setBatchIndex(-1)
        super().initWithKwargs(**kwargs)
        self.mode = self.MODE_NORMAL

    def clickStart(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return

        # Check that bots are in the sim.
        if not self.bot_list:
            self.addErrorDialog(
                '<font color="#DD4045">In order to run a simulation you must first select bots to use in the simulation.</font>'
                + "<br><br>You can add bots to the simulation by clicking the button under the settings cog after selecting a particular batch."
            )
            return

        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SIM, batch=self.available_batches[self.batch_index][1]
        )

    def clickSettings(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        import importlib
        from ev3sim.visual.manager import ScreenObjectManager

        with open(self.available_batches[self.batch_index][1], "r") as f:
            conf = yaml.safe_load(f)
        with open(find_abs(conf["preset_file"], preset_locations())) as f:
            preset = yaml.safe_load(f)
        mname, cname = preset["visual_settings"].rsplit(".", 1)

        klass = getattr(importlib.import_module(mname), cname)

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SETTINGS,
            file=self.available_batches[self.batch_index][1],
            settings=klass,
            allows_filename_change=not self.available_batches[self.batch_index][2].startswith("package"),
            extension="sim",
        )

        def onSave(filename):
            self.regenerateObjects()

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].onSave = onSave

    def addBatchDialog(self):
        self.mode = self.MODE_BATCH
        self.regenerateObjects()

    def generateBatch(self, preset_index):
        import importlib
        from ev3sim.visual.manager import ScreenObjectManager

        mname, cname = self.available_presets[preset_index][4]["visual_settings"].rsplit(".", 1)
        visual_settings = getattr(importlib.import_module(mname), cname)

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SETTINGS,
            settings=visual_settings,
            creating=True,
            creation_area="workspace/sims/",
            starting_data={
                "preset_file": f"{self.available_presets[preset_index][0]}.yaml",
                "bots": [],
                "settings": {
                    self.available_presets[preset_index][0]: {},
                },
            },
            extension="sim",
        )

        def onSave(filename):
            self.regenerateObjects()

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
        self.setBatchIndex(-1)

    def createBotImage(self, index):

        fname = find_abs(self.bot_list[index], bot_locations())
        with open(fname, "r") as f:
            config = yaml.safe_load(f)
        bot_preview = find_abs(config["preview_path"], allowed_areas=asset_locations())
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
        super().handleEvent(event)
        if self.mode == self.MODE_NORMAL:
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
        self.start_enable = new_index != -1
        self.settings_enable = new_index != -1
        self.bot_enable = new_index != -1
        self.remove_enable = new_index != -1 and not self.available_batches[new_index][2].startswith("package")
        self.regenerateObjects()

    def incrementBatchIndex(self, amount):
        if self.batch_index == -1:
            new_index = amount if amount < 0 else amount - 1
        else:
            new_index = self.batch_index + amount
        new_index %= len(self.batch_buttons)
        self.setBatchIndex(new_index)

    def onPop(self):
        self.setBatchIndex(-1)
