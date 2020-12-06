from ev3sim.visual.menus.utils import CustomScroll
import yaml
import os
import pygame
import pygame_gui
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.bot_files import BotValidator
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.search_locations import asset_locations, bot_locations, preset_locations


class BotMenu(BaseMenu):

    bot_keys = []

    def sizeObjects(self):
        button_size = self._size[0] / 4, 60
        info_size = self._size[0] / 4 - 20, 15
        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        settings_size = preview_size[0] * 0.4, preview_size[1] * 0.4
        settings_icon_size = settings_size[1] * 0.6, settings_size[1] * 0.6
        new_size = self._size[0] / 8, min(self._size[1] / 6, 90)
        new_icon_size = new_size[1] * 0.6, new_size[1] * 0.6
        bot_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
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
        for i in range(len(self.bot_buttons)):
            self.bot_buttons[i].set_dimensions(button_size)
            self.bot_buttons[i].set_position(bot_rect(i))
            self.bot_descriptions[i].set_dimensions(info_size)
            self.bot_descriptions[i].set_position(info_rect(bot_rect(i)))
        self.preview_image.set_dimensions(preview_size)
        self.preview_image.set_position((self._size[0] * 0.9 - preview_size[0], self._size[1] * 0.1))
        n_bot_spots = len(self.bot_keys)
        if n_bot_spots == 0:
            settings_button_pos = (
                self._size[0] * 0.9 - settings_size[0] - 10,
                self._size[1] * 0.1 + preview_size[1] + 10,
            )
            self.settings_button.set_dimensions(settings_size)
            self.settings_button.set_position(settings_button_pos)
            self.settings_icon.set_dimensions(settings_icon_size)
            self.settings_icon.set_position(
                (
                    settings_button_pos[0] + settings_size[0] / 2 - settings_icon_size[0] / 2,
                    settings_button_pos[1] + settings_size[1] * 0.2,
                )
            )
            edit_button_pos = (
                self._size[0] * 0.9 - preview_size[0],
                self._size[1] * 0.1 + preview_size[1] + 10,
            )
            self.edit_button.set_dimensions(settings_size)
            self.edit_button.set_position(edit_button_pos)
            self.edit_icon.set_dimensions(settings_icon_size)
            self.edit_icon.set_position(
                (
                    edit_button_pos[0] + settings_size[0] / 2 - settings_icon_size[0] / 2,
                    edit_button_pos[1] + settings_size[1] * 0.2,
                )
            )
            self.new_bot.set_dimensions(new_size)
            new_bot_pos = (bot_rect(0)[0] + button_size[0] - new_size[0], self._size[1] * 0.9 - new_size[1])
            self.new_bot.set_position(new_bot_pos)
            self.new_icon.set_dimensions(new_icon_size)
            self.new_icon.set_position(
                (
                    new_bot_pos[0] + new_size[0] / 2 - new_icon_size[0] / 2,
                    new_bot_pos[1] + new_size[1] * 0.2,
                )
            )
            self.remove_bot.set_dimensions(new_size)
            remove_bot_pos = (bot_rect(0)[0], self._size[1] * 0.9 - new_size[1])
            self.remove_bot.set_position(remove_bot_pos)
            self.remove_icon.set_dimensions(new_icon_size)
            self.remove_icon.set_position(
                (
                    remove_bot_pos[0] + new_size[0] / 2 - new_icon_size[0] / 2,
                    remove_bot_pos[1] + new_size[1] * 0.2,
                )
            )
        else:
            for i in range(n_bot_spots):
                self.sizeBotImage(i, big_mode=n_bot_spots < 1)
            select_size = (self._size[0] / 4 - 20) / 2, min(self._size[1] / 4, 120)
            done_size = (self._size[0] / 4 - 20) / 2, min(self._size[1] / 4, 120)
            self.select_button.set_dimensions(select_size)
            self.done_button.set_dimensions(done_size)
            select_button_pos = (self._size[0] * 0.9 - select_size[0] * 2 - 15, self._size[1] * 0.9 - select_size[1])
            done_button_pos = (self._size[0] * 0.9 - select_size[0] - 5, self._size[1] * 0.9 - select_size[1])
            self.select_button.set_position(select_button_pos)
            self.done_button.set_position(done_button_pos)

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
        bot_search_locations = (
            [b for b in bot_locations if "package" not in b] if len(self.bot_keys) == 0 else bot_locations
        )
        for rel_dir in bot_search_locations:
            try:
                actual_dir = find_abs_directory(rel_dir)
            except:
                continue
            for bot in BotValidator.all_valid_in_dir(actual_dir):
                # Show everything except dir and .yaml
                self.available_bots.append((bot[:-5], os.path.join(actual_dir, bot), rel_dir, bot))
        self.bot_buttons = []
        self.bot_descriptions = []

        self.scrolling_container = CustomScroll(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("scroll_container"),
        )
        self.scrolling_container.num_elems = len(self.available_bots)
        for i, (show, bot, rel_dir, filename) in enumerate(self.available_bots):
            self.bot_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=dummy_rect,
                    text=show,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "list_button"),
                )
            )
            self.bot_descriptions.append(
                pygame_gui.elements.UILabel(
                    relative_rect=dummy_rect,
                    text=rel_dir,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(show + "-dir-" + str(i), "button_info"),
                )
            )
        self._all_objs.extend(self.bot_buttons)
        self._all_objs.extend(self.bot_descriptions)
        image = pygame.Surface(self._size)
        image.fill(pygame.Color(self.bg.background_colour))
        self.preview_image = pygame_gui.elements.UIImage(
            relative_rect=dummy_rect,
            image_surface=image,
            manager=self,
            object_id=pygame_gui.core.ObjectID("preview-image"),
        )
        self._all_objs.append(self.preview_image)
        if len(self.bot_keys) == 0:
            self.settings_button = pygame_gui.elements.UIButton(
                relative_rect=dummy_rect,
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("bot-settings", "settings_buttons"),
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
            self.edit_button = pygame_gui.elements.UIButton(
                relative_rect=dummy_rect,
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("bot-edit", "settings_buttons"),
            )
            edit_icon_path = find_abs("ui/edit.png", allowed_areas=asset_locations)
            self.edit_icon = pygame_gui.elements.UIImage(
                relative_rect=dummy_rect,
                image_surface=pygame.image.load(edit_icon_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("edit-icon"),
            )
            self._all_objs.append(self.edit_button)
            self._all_objs.append(self.edit_icon)
            self.new_bot = pygame_gui.elements.UIButton(
                relative_rect=dummy_rect,
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("new_bot", "action_button"),
            )
            new_bot_path = find_abs("ui/add.png", allowed_areas=asset_locations)
            self.new_icon = pygame_gui.elements.UIImage(
                relative_rect=dummy_rect,
                image_surface=pygame.image.load(new_bot_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("new_bot-icon"),
            )
            self._all_objs.append(self.new_bot)
            self._all_objs.append(self.new_icon)
            self.remove_bot = pygame_gui.elements.UIButton(
                relative_rect=dummy_rect,
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("remove_bot", "cancel-changes"),
            )
            remove_bot_path = find_abs("ui/bin.png", allowed_areas=asset_locations)
            self.remove_icon = pygame_gui.elements.UIImage(
                relative_rect=dummy_rect,
                image_surface=pygame.image.load(remove_bot_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("remove_bot-icon"),
            )
            self._all_objs.append(self.remove_bot)
            self._all_objs.append(self.remove_icon)
        else:
            # Bot key locations, for selecting bots in batch files.
            self.bot_loc_spots = []
            for i in range(len(self.bot_keys)):
                self.bot_loc_spots.append(self.createBotImage(i))
            self._all_objs.extend(self.bot_loc_spots)
            self.select_button = pygame_gui.elements.UIButton(
                relative_rect=dummy_rect,
                text="SELECT",
                manager=self,
                object_id=pygame_gui.core.ObjectID("select-bot", "action_button"),
            )
            self._all_objs.append(self.select_button)
            self.done_button = pygame_gui.elements.UIButton(
                relative_rect=dummy_rect,
                text="DONE",
                manager=self,
                object_id=pygame_gui.core.ObjectID("select-done", "action_button"),
            )
            self._all_objs.append(self.done_button)

    def createBotImage(self, index, bg=None):
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.visual.utils import worldspace_to_screenspace
        from ev3sim.visual.objects import Text

        width = 0
        lengths = []
        surfaces = []
        for text_line in self.bot_keys[index].replace("\\n", "\n").split("\n"):
            text_object = Text()
            text_object.initFromKwargs(
                text=text_line,
                hAlignment="m",
                vAlignment="m",
            )
            named_surface = ScreenObjectManager.instance.screen.copy()
            named_surface.fill(pygame.Color("#181A25") if bg is None else bg)
            text_object.applyToScreen(named_surface)
            surfaces.append(named_surface)
            lengths.append(text_object.rect.height)
            width = max(width, text_object.rect.width)
        line_spacing = 10
        s = max(width, sum(lengths) + (len(lengths) - 1) * line_spacing) + 30
        pos = worldspace_to_screenspace((0, 0))
        cropped_surface = pygame.Surface((s, s))
        cropped_surface.fill(pygame.Color("#181A25") if bg is None else bg)
        cur_y = (s - (sum(lengths) + (len(lengths) - 1) * line_spacing)) // 2
        for y, surface in zip(lengths, surfaces):
            cropped_surface.blit(surface, (0, cur_y), (pos[0] - s // 2, pos[1] - (y + 1) // 2 - 1, s, y + 2))
            cur_y += y + line_spacing
        return pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(0, 0, *self._size),
            image_surface=cropped_surface,
            manager=self,
            object_id=pygame_gui.core.ObjectID(f"bot-image-{self.bot_keys[index]}"),
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

    def initWithKwargs(self, **kwargs):
        self.bot_index = -1
        batch = kwargs.get("batch_file", None)
        self.batch = batch
        if batch is None:
            # We are simply viewing the bots to edit or manage.
            self.bot_keys = []
        else:
            self.key_index = 0
            with open(batch, "r") as f:
                b_config = yaml.safe_load(f)
            preset = b_config["preset_file"]
            fname = find_abs(preset, allowed_areas=preset_locations)
            with open(fname, "r") as f:
                p_config = yaml.safe_load(f)
            self.bot_keys = p_config["bot_names"]
            self.bot_values = [None] * len(self.bot_keys)
        super().initWithKwargs(**kwargs)
        if len(self.bot_keys) > 0:
            self.highlightBotSelectIndex(0)
            self.select_button.disable()
        else:
            self.settings_button.disable()
            self.edit_button.disable()
            self.remove_bot.disable()

    def clickEdit(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_BOT_EDIT,
            bot_file=self.available_bots[self.bot_index][1],
            bot_dir_file=self.available_bots[self.bot_index][2:4],
        )

        bot_index = self.bot_index

        def onSave(filename):
            self.clearObjects()
            self.generateObjects()
            self.sizeObjects()
            self.setBotIndex(bot_index)

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].onSave = onSave

    def clickSettings(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager
        from ev3sim.robot import visual_settings

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SETTINGS,
            file=self.available_bots[self.bot_index][1],
            settings=visual_settings,
            allows_filename_change=not self.available_bots[self.bot_index][2].startswith("package"),
        )

        def onSave(filename):
            self.clearObjects()
            self.generateObjects()
            self.sizeObjects()

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SETTINGS].onSave = onSave

    def clickSelect(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        self.setBotAtIndex(self.key_index)
        self.incrementBotSelectIndex()
        self.setBotIndex(-1)

    def clickDone(self):
        with open(self.batch, "r") as f:
            json_obj = yaml.safe_load(f)
        json_obj["bots"] = [x for x in self.bot_values if x is not None]
        string = yaml.dump(json_obj)
        with open(self.batch, "w") as f:
            f.write(string)
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.popScreen()
        # Make sure the batch screen updates.
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BATCH].setBatchIndex(
            ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BATCH].batch_index
        )

    def clickNew(self):
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BOT_EDIT)

        def onSave(filename):
            self.clearObjects()
            self.generateObjects()
            self.sizeObjects()
            self.setBotIndex(len(self.bot_descriptions) - 1)

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].onSave = onSave

    def clickRemove(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        os.remove(self.available_bots[self.bot_index][1])
        self.clearObjects()
        self.generateObjects()
        self.sizeObjects()
        self.setBotIndex(-1)

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id.startswith("bot-settings"):
                self.clickSettings()
            elif event.ui_object_id.startswith("bot-edit"):
                self.clickEdit()
            elif event.ui_object_id.startswith("select-bot"):
                self.clickSelect()
            elif event.ui_object_id.startswith("select-done"):
                self.clickDone()
            elif event.ui_object_id.startswith("new_bot"):
                self.clickNew()
            elif event.ui_object_id.startswith("remove_bot"):
                self.clickRemove()
            else:
                if event.ui_object_id.split("#")[0].split("-")[-1].isnumeric():
                    self.setBotIndex(int(event.ui_object_id.split("#")[0].split("-")[-1]))
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBotIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBotIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickSettings()

    def setBotIndex(self, new_index):
        self.bot_index = new_index
        if len(self.bot_keys) == 0:
            if new_index == -1:
                self.settings_button.disable()
                self.edit_button.disable()
                self.remove_bot.disable()
            else:
                self.settings_button.enable()
                self.edit_button.enable()
                if self.available_bots[self.bot_index][2].startswith("package"):
                    self.remove_bot.disable()
                else:
                    self.remove_bot.enable()
        else:
            if new_index == -1:
                self.select_button.disable()
            else:
                self.select_button.enable()
        for i in range(len(self.bot_buttons)):
            self.bot_buttons[i].combined_element_ids[2] = (
                "list_button_highlighted" if i == self.bot_index else "list_button"
            )
            self.bot_buttons[i].rebuild_from_changed_theme_data()
            self.bot_descriptions[i].combined_element_ids[2] = (
                "button_info_selected" if i == self.bot_index else "button_info"
            )
            self.bot_descriptions[i].rebuild_from_changed_theme_data()
        self.blitCurrentBotPreview()

    def blitCurrentBotPreview(self):
        if self.bot_index == -1:
            img = pygame.Surface(self._size)
            img.fill(pygame.Color(self.bg.background_colour))
        else:
            with open(self.available_bots[self.bot_index][1], "r") as f:
                config = yaml.safe_load(f)
            bot_preview = find_abs(config["preview_path"], allowed_areas=asset_locations)
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

    def setBotAtIndex(self, index):
        self.bot_values[index] = (
            self.available_bots[self.bot_index][0] + "." + self.available_bots[self.bot_index][1].split(".")[-1]
        )
        with open(self.available_bots[self.bot_index][1], "r") as f:
            config = yaml.safe_load(f)
        bot_preview = find_abs(config["preview_path"], allowed_areas=asset_locations)
        img = pygame.image.load(bot_preview)
        if img.get_size() != self.bot_loc_spots[index].rect.size:
            img = pygame.transform.smoothscale(
                img, (self.bot_loc_spots[index].rect.width, self.bot_loc_spots[index].rect.height)
            )
        self.bot_loc_spots[index].set_image(img)

    def highlightBotSelectIndex(self, index):
        self._all_objs.remove(self.bot_loc_spots[index])
        self.bot_loc_spots[index].kill()
        self.bot_loc_spots[index] = self.createBotImage(index, bg=pygame.Color("#80b918"))
        self._all_objs.append(self.bot_loc_spots[index])
        self.sizeBotImage(index, big_mode=len(self.bot_keys) < 1)

    def incrementBotSelectIndex(self):
        # Select the next key
        self.key_index += 1
        if self.key_index == len(self.bot_keys):
            # We've selected all the bots. Save.
            self.clickDone()
        else:
            # Highlight the next position.
            self.highlightBotSelectIndex(self.key_index)

    def onPop(self):
        self.bot_index = -1
        if len(self.bot_keys) == 0:
            self.settings_button.disable()
            self.remove_bot.disable()
            self.edit_button.disable()
        else:
            self.select_button.disable()
        for i in range(len(self.bot_buttons)):
            self.bot_buttons[i].combined_element_ids[2] = "list_button"
            self.bot_buttons[i].rebuild_from_changed_theme_data()
            self.bot_descriptions[i].combined_element_ids[2] = "button_info"
            self.bot_descriptions[i].rebuild_from_changed_theme_data()
