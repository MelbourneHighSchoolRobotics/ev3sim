from ev3sim.visual.menus.utils import CustomScroll
import yaml
import os
import pygame
import pygame_gui
import sentry_sdk
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.bot_files import BotValidator
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.search_locations import asset_locations, bot_locations, preset_locations


class BotMenu(BaseMenu):

    bot_keys = []

    def iconPos(self, buttonPos, buttonSize, iconSize):
        return (
            buttonPos[0] + buttonSize[0] / 2 - iconSize[0] / 2,
            buttonPos[1] + buttonSize[1] * 0.2,
        )

    def generateObjects(self):
        # First, find all bot files.
        if not self.in_error:
            self.available_bots = []
            error_bots = []
            for rel_dir in bot_locations():
                try:
                    actual_dir = find_abs_directory(rel_dir)
                except:
                    continue
                for bot in BotValidator.all_valid_in_dir(actual_dir):
                    try:
                        # Show everything except dir and .bot
                        with open(os.path.join(actual_dir, bot, "config.bot"), "r") as f:
                            config = yaml.safe_load(f)
                        # If we are hidden, or in edit mode with hidden_edit, then don't show.
                        if not config.get("hidden", False) and not (
                            config.get("hidden_edit", False) and len(self.bot_keys) == 0
                        ):
                            self.available_bots.append((bot, os.path.join(actual_dir, bot), rel_dir, bot))
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
                        error_bots.append(os.path.join(actual_dir, bot))
            if self.first_launch and error_bots:
                self.first_launch = False
                self.in_error = True
                self.addErrorDialog(
                    'A problem occured loading the following bots:<br><br><font color="#cc0000">'
                    + "<br>".join(bot for bot in error_bots)
                    + "</font>"
                )
                return

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
            relative_rect=pygame.Rect(0, 0, *self._size),
            manager=self,
            object_id=pygame_gui.core.ObjectID("scroll_container"),
        )
        self.scrolling_container.num_elems = len(self.available_bots)
        scrolling_size = (self._size[0] / 4 + self._size[0] / 5, self._size[1] * 0.9 - min(self._size[1] / 6, 90))
        # Setting dimensions and positions on a UIScrollingContainer seems buggy. This works.
        self.scrolling_container.set_dimensions(scrolling_size)
        self.scrolling_container.set_position(scrolling_size)
        self.scrolling_container.cur_y = old_y
        self.scrolling_container.set_scroll(old_y)
        self._all_objs.append(self.scrolling_container)

        button_size = self._size[0] / 4, 60
        info_size = self._size[0] / 4 - 20, 15
        bot_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        info_rect = lambda b_r: (
            b_r[0] + button_size[0] - info_size[0] - 10,
            b_r[1] + button_size[1] - info_size[1] - 5,
        )
        self.bot_buttons = []
        self.bot_descriptions = []
        for i, (show, bot, rel_dir, filename) in enumerate(self.available_bots):
            self.bot_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(*bot_rect(i), *button_size),
                    text=show,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(
                        show + "-" + str(i), "list_button_highlighted" if i == self.bot_index else "list_button"
                    ),
                )
            )
            self.addButtonEvent(show + "-" + str(i), self.setBotIndex, i)
            self.bot_descriptions.append(
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(*info_rect(bot_rect(i)), *info_size),
                    text=rel_dir,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(
                        show + "-dir-" + str(i), "button_info_selected" if i == self.bot_index else "button_info"
                    ),
                )
            )
        self._all_objs.extend(self.bot_buttons)
        self._all_objs.extend(self.bot_descriptions)

        preview_size = self._size[0] / 4, self._size[1] / 4
        preview_size = (
            min(preview_size[0], (preview_size[1] * 4) // 3),
            min(preview_size[1], (preview_size[0] * 3) // 4),
        )
        try:
            if self.bot_index >= len(self.available_bots):
                self.bot_index = -1
            if self.bot_index == -1:
                image = pygame.Surface(preview_size)
                image.fill(pygame.Color(self.bg.background_colour))
            else:
                with open(os.path.join(self.available_bots[self.bot_index][1], "config.bot"), "r") as f:
                    config = yaml.safe_load(f)
                bot_preview = os.path.join(
                    self.available_bots[self.bot_index][1], config.get("preview_path", "preview.png")
                )
                image = pygame.image.load(bot_preview)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.setBotIndex(-1)
            self.addErrorDialog(
                '<font color="#cc0000">The bot you have selected has some internal errors EV3Sim cannot resolve.</font><br><br>'
                + "If you'd like to fix this, then try manually editing the bot file in a text editor."
            )
            return
        if image.get_size() != preview_size:
            image = pygame.transform.smoothscale(image, [int(v) for v in preview_size])
        self.preview_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(self._size[0] * 0.9 - preview_size[0], self._size[1] * 0.1, *preview_size),
            image_surface=image,
            manager=self,
            object_id=pygame_gui.core.ObjectID("preview-image"),
        )
        self._all_objs.append(self.preview_image)

        if len(self.bot_keys) == 0:
            code_size = preview_size[0] * 0.4, preview_size[1] * 0.4
            code_button_pos = (
                self._size[0] * 0.9 - code_size[0] - 10,
                self._size[1] * 0.1 + preview_size[1] + 10,
            )
            code_icon_size = code_size[1] * 0.6, code_size[1] * 0.6
            self.code_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*code_button_pos, *code_size),
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("bot-code", "settings_buttons"),
            )
            self.addButtonEvent("bot-code", self.clickCode)
            if not self.code_enable:
                self.code_button.disable()
            code_icon_path = find_abs("ui/code.png", allowed_areas=asset_locations())
            self.code_icon = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(*self.iconPos(code_button_pos, code_size, code_icon_size), *code_icon_size),
                image_surface=pygame.image.load(code_icon_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("code-icon"),
            )
            self._all_objs.append(self.code_button)
            self._all_objs.append(self.code_icon)

            edit_button_pos = (
                self._size[0] * 0.9 - preview_size[0],
                self._size[1] * 0.1 + preview_size[1] + 10,
            )
            self.edit_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*edit_button_pos, *code_size),
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("bot-edit", "settings_buttons"),
            )
            self.addButtonEvent("bot-edit", self.clickEdit)
            if not self.edit_enable:
                self.edit_button.disable()
            edit_icon_path = find_abs("ui/edit.png", allowed_areas=asset_locations())
            self.edit_icon = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(*self.iconPos(edit_button_pos, code_size, code_icon_size), *code_icon_size),
                image_surface=pygame.image.load(edit_icon_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("edit-icon"),
            )
            self._all_objs.append(self.edit_button)
            self._all_objs.append(self.edit_icon)

            new_size = self._size[0] / 8, min(self._size[1] / 6, 90)
            new_icon_size = new_size[1] * 0.6, new_size[1] * 0.6
            new_bot_pos = (bot_rect(0)[0] + button_size[0] - new_size[0], self._size[1] * 0.9 - new_size[1])
            self.new_bot = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*new_bot_pos, *new_size),
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("new_bot", "action_button"),
            )
            self.addButtonEvent("new_bot", self.clickNew)
            new_bot_path = find_abs("ui/add.png", allowed_areas=asset_locations())
            self.new_icon = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(*self.iconPos(new_bot_pos, new_size, new_icon_size), *new_icon_size),
                image_surface=pygame.image.load(new_bot_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("new_bot-icon"),
            )
            self._all_objs.append(self.new_bot)
            self._all_objs.append(self.new_icon)

            remove_bot_pos = (bot_rect(0)[0], self._size[1] * 0.9 - new_size[1])
            self.remove_bot = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*remove_bot_pos, *new_size),
                text="",
                manager=self,
                object_id=pygame_gui.core.ObjectID("remove_bot", "cancel-changes"),
            )
            self.addButtonEvent("remove_bot", self.clickRemove)
            if not self.remove_enable:
                self.remove_bot.disable()
            remove_bot_path = find_abs("ui/bin.png", allowed_areas=asset_locations())
            self.remove_icon = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(*self.iconPos(remove_bot_pos, new_size, new_icon_size), *new_icon_size),
                image_surface=pygame.image.load(remove_bot_path),
                manager=self,
                object_id=pygame_gui.core.ObjectID("remove_bot-icon"),
            )
            self._all_objs.append(self.remove_bot)
            self._all_objs.append(self.remove_icon)
            super().generateObjects()
        else:
            # Bot key locations, for selecting bots in batch files.
            self.bot_loc_spots = []
            for i in range(len(self.bot_keys)):
                if i == self.key_index:
                    self.bot_loc_spots.append(self.createBotImage(i, bg=pygame.Color("#80b918")))
                else:
                    self.bot_loc_spots.append(self.createBotImage(i))
                self.sizeBotImage(i, big_mode=len(self.bot_keys) == 1)
                img = self.preview_images[i]
                if img is None:
                    continue
                if img.get_size() != self.bot_loc_spots[i].rect.size:
                    img = pygame.transform.smoothscale(
                        img, (self.bot_loc_spots[i].rect.width, self.bot_loc_spots[i].rect.height)
                    )
                self.bot_loc_spots[i].set_image(img)
            self._all_objs.extend(self.bot_loc_spots)

            select_size = (self._size[0] / 4 - 20) / 2, min(self._size[1] / 4, 120)
            select_button_pos = (self._size[0] * 0.9 - select_size[0] * 2 - 15, self._size[1] * 0.9 - select_size[1])
            self.select_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*select_button_pos, *select_size),
                text="SELECT",
                manager=self,
                object_id=pygame_gui.core.ObjectID("select-bot", "action_button"),
            )
            self.addButtonEvent("select-bot", self.clickSelect)
            if not self.select_enable:
                self.select_button.disable()
            self._all_objs.append(self.select_button)

            done_size = (self._size[0] / 4 - 20) / 2, min(self._size[1] / 4, 120)
            done_button_pos = (self._size[0] * 0.9 - select_size[0] - 5, self._size[1] * 0.9 - select_size[1])
            self.done_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*done_button_pos, *done_size),
                text="DONE",
                manager=self,
                object_id=pygame_gui.core.ObjectID("select-done", "action_button"),
            )
            self.addButtonEvent("select-done", self.clickDone)
            if self.key_index == 0:
                self.done_button.disable()
            self._all_objs.append(self.done_button)
            super().generateObjects()

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
        self.in_error = False
        self.first_launch = True
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
            fname = find_abs(preset, allowed_areas=preset_locations())
            with open(fname, "r") as f:
                p_config = yaml.safe_load(f)
            self.bot_keys = p_config["bot_names"]
            self.bot_values = [None] * len(self.bot_keys)
            self.preview_images = [None] * len(self.bot_keys)
        self.bot_select_index = 0
        self.select_enable = False
        self.code_enable = False
        self.edit_enable = False
        self.remove_enable = False
        self.bot_index = -1
        self.next = kwargs.get("next", None)
        self.next_kwargs = kwargs.get("next_kwargs", {})
        super().initWithKwargs(**kwargs)

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

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].clearEvents()

    def clickCode(self):
        from ev3sim.utils import open_file, APP_VSCODE, APP_MINDSTORMS

        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        with open(os.path.join(self.available_bots[self.bot_index][1], "config.bot")) as f:
            conf = yaml.safe_load(f)

        if conf.get("type", "python") == "mindstorms":
            script_location = conf.get("script", "program.ev3")

            open_file(os.path.join(self.available_bots[self.bot_index][1], script_location), APP_MINDSTORMS)
        else:
            script_location = conf.get("script", "code.py")

            open_file(
                os.path.join(self.available_bots[self.bot_index][1], script_location),
                APP_VSCODE,
                folder=os.path.join(find_abs_directory("workspace")),
            )

    def clickSelect(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        self.setBotAtIndex(self.key_index)
        self.incrementBotSelectIndex()
        self.regenerateObjects()

    def clickDone(self):
        with open(self.batch, "r") as f:
            json_obj = yaml.safe_load(f)
        json_obj["bots"] = [x for x in self.bot_values if x is not None]
        string = yaml.dump(json_obj)
        with open(self.batch, "w") as f:
            f.write(string)
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.popScreen()
        if self.next is not None:
            ScreenObjectManager.instance.pushScreen(self.next, **self.next_kwargs)

    def clickNew(self):
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BOT_EDIT)

        def onSave(filename):
            self.regenerateObjects()
            for i, (_, _, _, bot) in enumerate(self.available_bots):
                if bot == filename:
                    self.setBotIndex(i)

        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].clearEvents()
        ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_BOT_EDIT].onSave = onSave

    def clickRemove(self):
        # Shouldn't happen but lets be safe.
        if self.bot_index == -1:
            return
        import shutil

        shutil.rmtree(self.available_bots[self.bot_index][1])
        self.setBotIndex(-1)

    def handleEvent(self, event):
        super().handleEvent(event)
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBotIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBotIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickCode()

    def setBotIndex(self, new_index):
        self.bot_index = new_index
        if len(self.bot_keys) == 0:
            self.code_enable = new_index != -1
            self.edit_enable = new_index != -1
            self.remove_enable = new_index != -1 and not self.available_bots[new_index][2].startswith("package")
        else:
            self.select_enable = new_index != -1
        self.regenerateObjects()

    def incrementBotIndex(self, amount):
        if self.bot_index == -1:
            new_index = len(self.available_bots) + amount if amount < 0 else amount - 1
        else:
            new_index = self.bot_index + amount
        new_index %= len(self.bot_buttons)
        self.setBotIndex(new_index)

    def setBotAtIndex(self, index):
        self.bot_values[index] = self.available_bots[self.bot_index][0]
        with open(os.path.join(self.available_bots[self.bot_index][1], "config.bot"), "r") as f:
            config = yaml.safe_load(f)
        bot_preview = os.path.join(self.available_bots[self.bot_index][1], config.get("preview_path", "preview.png"))
        self.preview_images[index] = pygame.image.load(bot_preview)
        self.regenerateObjects()

    def incrementBotSelectIndex(self):
        # Select the next key
        self.key_index += 1
        if self.key_index == len(self.bot_keys):
            # We've selected all the bots. Save.
            self.clickDone()
        else:
            # Update the screen.
            self.regenerateObjects()

    def onPop(self):
        self.setBotIndex(-1)
