from ev3sim.visual.menus.utils import CustomScroll
import yaml
import os
import pygame
import pygame_gui
import sentry_sdk
from ev3sim.file_helper import find_abs, find_abs_directory, make_relative
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.search_locations import asset_locations, batch_locations, bot_locations


class BatchMenu(BaseMenu):
    def iconPos(self, buttonPos, buttonSize, iconSize):
        return (
            buttonPos[0] + buttonSize[0] / 2 - iconSize[0] / 2,
            buttonPos[1] + buttonSize[1] * 0.2,
        )

    def generateObjects(self):
        # First, find all batch files.
        if not self.in_error:
            self.available_batches = []
            error_batches = []
            for rel_dir in batch_locations():
                # Only show custom sims.
                if not rel_dir.startswith("workspace/custom/"):
                    continue
                try:
                    actual_dir = find_abs_directory(rel_dir)
                except:
                    continue
                for batch in BatchValidator.all_valid_in_dir(actual_dir):
                    # Show the dir name.
                    try:
                        with open(os.path.join(actual_dir, batch), "r") as f:
                            config = yaml.safe_load(f)
                        if not config.get("hidden", False):
                            rest = rel_dir
                            directory = ""
                            while not directory:
                                rest, directory = os.path.split(rest)
                            self.available_batches.append(
                                (directory, os.path.join(actual_dir, batch), actual_dir, batch)
                            )
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
                        error_batches.append(os.path.join(actual_dir, batch))
            if self.first_launch and error_batches:
                self.first_launch = False
                self.in_error = True
                self.addErrorDialog(
                    'A problem occured loading the following batches:<br><br><font color="#cc0000">'
                    + "<br>".join(batch for batch in error_batches)
                    + "</font>"
                )
                return

        for i, batch in enumerate(self.available_batches):
            if i == self.batch_index:
                try:
                    with open(batch[1], "r") as f:
                        config = yaml.safe_load(f)
                    # Update batch information
                    preset_path = find_abs(config["preset_file"], allowed_areas=["workspace"])
                    with open(preset_path, "r") as f:
                        preset_config = yaml.safe_load(f)
                    preset_preview = find_abs(preset_config["preview_path"], allowed_areas=["workspace"])
                    self.preview_image_source = pygame.image.load(preset_preview)
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    self.setBatchIndex(-1)
                    self.addErrorDialog(
                        '<font color="#cc0000">The task you have selected has some internal errors EV3Sim cannot resolve.</font><br><br>'
                        + "This can be caused by moving/renaming a bot as well as a few other things.<br><br>"
                        + "If you'd like to fix this, then try manually editing the sim file in a text editor or contact the developers."
                    )
                    return

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
        button_size = self._size[0] / 4, 60
        info_size = self._size[0] / 4 - 20, 15
        batch_rect = lambda i: (self._size[0] / 10, self._size[1] / 10 + i * button_size[1] * 1.5)
        info_rect = lambda b_r: (
            b_r[0] + button_size[0] - info_size[0] - 10,
            b_r[1] + button_size[1] - info_size[1] - 5,
        )
        self.batch_buttons = []
        for i, (show, batch, actual_dir, filename) in enumerate(self.available_batches):
            self.batch_buttons.append(
                pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(*batch_rect(i), *button_size),
                    text=show,
                    manager=self,
                    container=self.scrolling_container,
                    object_id=pygame_gui.core.ObjectID(show + "-" + str(i), "list_button"),
                )
            )
            self.addButtonEvent(show + "-" + str(i), self.setBatchIndex, i)

        self._all_objs.extend(self.batch_buttons)

        # Remove
        remove_size = self._size[0] / 8, min(self._size[1] / 6, 90)
        remove_icon_size = remove_size[1] * 0.6, remove_size[1] * 0.6
        remove_batch_pos = (self._size[0] / 3 - 2 * remove_size[0] - 15, self._size[1] * 0.95 - remove_size[1])
        self.remove_batch = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*remove_batch_pos, *remove_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("remove_batch", "cancel-changes"),
        )
        self.addButtonEvent("remove_batch", self.clickRemove)
        if not self.remove_enable:
            self.remove_batch.disable()
        remove_batch_path = find_abs("ui/bin.png", allowed_areas=asset_locations())
        self.remove_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(
                *self.iconPos(remove_batch_pos, remove_size, remove_icon_size), *remove_icon_size
            ),
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

        bots_button_pos = (
            self._size[0] * 0.9 - preview_size[0] + 10,
            self._size[1] * 0.1 + preview_size[1] + 10,
        )
        self.bots_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*bots_button_pos, *code_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("bot-bots", "settings_buttons"),
        )
        self.addButtonEvent("bot-bots", self.clickBots)
        if not self.bots_enable:
            self.bots_button.disable()
        bots_icon_path = find_abs("ui/bot.png", allowed_areas=asset_locations())
        self.bots_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(bots_button_pos, code_size, code_icon_size), *code_icon_size),
            image_surface=pygame.image.load(bots_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("bots-icon"),
        )
        self._all_objs.append(self.bots_button)
        self._all_objs.append(self.bots_icon)

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

        self.changeSelectedTheming()
        super().generateObjects()

    def changeSelectedTheming(self):
        for i in range(len(self.batch_buttons)):
            self.batch_buttons[i].combined_element_ids[1] = (
                "list_button_highlighted" if i == self.batch_index else "list_button"
            )
            self.batch_buttons[i].rebuild_from_changed_theme_data()
        if self.batch_index != -1:
            if self.preview_image_source.get_size() != self.preview_image.rect.size:
                self.preview_image_source = pygame.transform.smoothscale(
                    self.preview_image_source, (self.preview_image.rect.width, self.preview_image.rect.height)
                )
            self.preview_image.set_image(self.preview_image_source)

    def initWithKwargs(self, **kwargs):
        self.first_launch = True
        self.in_error = False
        self.setBatchIndex(-1)
        super().initWithKwargs(**kwargs)
        if "selected" in kwargs:
            for i, batch in enumerate(self.available_batches):
                if batch[1] == kwargs["selected"]:
                    self.setBatchIndex(i)

    def clickStart(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return

        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SIM, batch=self.available_batches[self.batch_index][1]
        )

    def clickBots(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        from ev3sim.visual.manager import ScreenObjectManager

        sim_path = self.available_batches[self.batch_index][1]

        with open(sim_path, "r") as f:
            sim_config = yaml.safe_load(f)

        complete_path = find_abs(sim_config["bots"][0], bot_locations())
        relative_dir, relative_path = make_relative(complete_path, bot_locations())

        return ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_BOT_EDIT,
            bot_file=complete_path,
            bot_dir_file=(relative_dir, relative_path),
        )

    def clickRemove(self):
        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        import shutil

        shutil.rmtree(self.available_batches[self.batch_index][2])
        self.setBatchIndex(-1)

    def clickCode(self):
        from ev3sim.utils import open_file, APP_VSCODE, APP_MINDSTORMS

        # Shouldn't happen but lets be safe.
        if self.batch_index == -1:
            return
        with open(os.path.join(self.available_batches[self.batch_index][2], "bot", "config.bot")) as f:
            conf = yaml.safe_load(f)
        if conf.get("type", "python") == "mindstorms":
            script_location = conf.get("script", "program.ev3")

            open_file(os.path.join(self.available_batches[self.batch_index][2], "bot", script_location), APP_MINDSTORMS)
        else:
            script_location = conf.get("script", "code.py")

            open_file(
                os.path.join(self.available_batches[self.batch_index][2], "bot", script_location),
                APP_VSCODE,
                folder=os.path.join(find_abs_directory("workspace")),
            )

    def handleEvent(self, event):
        super().handleEvent(event)
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_DOWN, pygame.K_w]:
                self.incrementBatchIndex(1)
            elif event.key in [pygame.K_UP, pygame.K_s]:
                self.incrementBatchIndex(-1)
            elif event.key == pygame.K_RETURN:
                self.clickStart()
            elif event.key in [pygame.K_DELETE, pygame.K_BACKSPACE]:
                self.clickRemove()

    def setBatchIndex(self, new_index):
        self.batch_index = new_index
        self.start_enable = new_index != -1
        self.remove_enable = new_index != -1
        self.code_enable = new_index != -1
        if new_index != -1:
            sim_path = self.available_batches[self.batch_index][1]

            with open(sim_path, "r") as f:
                sim_config = yaml.safe_load(f)
            self.bots_enable = sim_config.get("edit_allowed", True)
        else:
            self.bots_enable = False
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
