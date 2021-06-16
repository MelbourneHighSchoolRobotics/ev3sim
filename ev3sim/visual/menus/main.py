from ev3sim.visual.manager import ScreenObjectManager
from ev3sim.validation.bot_files import BotValidator
import os
import pygame
import pygame_gui
import yaml
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.validation.batch_files import BatchValidator
from ev3sim.visual.menus.base_menu import BaseMenu
from ev3sim.visual.settings.main_settings import main_settings
from ev3sim.search_locations import (
    asset_locations,
    batch_locations,
    bot_locations,
    code_locations,
    config_locations,
    preset_locations,
)


class MainMenu(BaseMenu):

    SLIDE_NUMS = 4
    SLIDE_TIME = 5

    def buttonPos(self, i):
        return (
            (self._size[0] - self.button_size[0]) / 2,
            (self._size[1] - self.button_size[1]) / 2
            + self.button_size[1] * (1.5 * i - (2.5 if self.show_custom else 2))
            + 50,
        )

    def playSim(self, preset):
        abs_path = find_abs(preset, allowed_areas=preset_locations())
        with open(abs_path, "r") as f:
            preset_config = yaml.safe_load(f)
        sim_path = find_abs(preset_config["sim_location"], allowed_areas=batch_locations())
        with open(sim_path, "r") as f:
            sim_config = yaml.safe_load(f)
        to_remove = []
        for index in range(len(sim_config["bots"])):
            # Try loading this bot.
            try:
                with open(os.path.join(find_abs(sim_config["bots"][index], bot_locations()), "config.bot"), "r") as f:
                    bot_config = yaml.safe_load(f)
                if not BotValidator.validate_json(bot_config):
                    to_remove.append(index)
                if bot_config.get("type", "python") == "python":
                    fname = bot_config.get("script", "code.py")
                else:
                    fname = bot_config.get("script", "program.ev3")
                if not os.path.exists(os.path.join(find_abs(sim_config["bots"][index], bot_locations()), fname)):

                    def action():
                        with open(os.path.join(find_abs(sim_config["bots"][index], bot_locations()), fname), "w") as f:
                            f.write("# Put your code here!\n")

                    ScreenObjectManager.instance.forceCloseError(
                        f"Your bot {sim_config['bots'][index]} does not contain the file {fname}. You may have renamed or deleted it by accident. In order to use this bot, you need to add this file back. Click \"Add {fname}\" to create this file, or do it manually.",
                        (f"Add {fname}", action),
                    )
                    return
            except:
                to_remove.append(index)
        if to_remove:
            for index in to_remove[::-1]:
                del sim_config["bots"][index]
            with open(sim_path, "w") as f:
                f.write(yaml.dump(sim_config))
        if not sim_config["bots"]:
            # We cannot play, there no are valid bots.
            return ScreenObjectManager.instance.pushScreen(
                ScreenObjectManager.SCREEN_BOTS,
                batch_file=sim_path,
                next=ScreenObjectManager.instance.SCREEN_SIM,
                next_kwargs={"batch": sim_path},
            )
        return ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.instance.SCREEN_SIM,
            batch=sim_path,
        )

    def iconPos(self, buttonPos, buttonSize, iconSize):
        return (
            buttonPos[0] + buttonSize[0] / 2 - iconSize[0] / 2,
            buttonPos[1] + buttonSize[1] * 0.2,
        )

    def generateObjects(self):
        from ev3sim.visual.manager import ScreenObjectManager

        self.show_custom = False
        # First, check if there are any valid batches in the custom folder.
        for rel_dir in batch_locations():
            # Only consider custom sims.
            if not rel_dir.startswith("workspace/custom/"):
                continue
            try:
                actual_dir = find_abs_directory(rel_dir)
            except:
                continue
            for _ in BatchValidator.all_valid_in_dir(actual_dir):
                self.show_custom = True
                break

        # In order to respect theme changes, objects must be built in initWithKwargs
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, *self._size),
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
        self.title.set_position(((self._size[0] - self.title.rect.width) / 2, 50))
        self._all_objs.append(self.title)

        self.button_size = (
            (self._size[0] / 4, self._size[1] / 10) if self.show_custom else (self._size[0] / 4, self._size[1] / 8)
        )
        settings_size = self.button_size[0] * 0.3, self.button_size[1]
        bot_size = settings_size
        settings_icon_size = settings_size[1] * 0.6, settings_size[1] * 0.6
        bot_icon_size = bot_size[1] * 0.6, bot_size[1] * 0.6
        settings_icon_path = find_abs("ui/settings.png", allowed_areas=asset_locations())
        bot_icon_path = find_abs("ui/bot.png", allowed_areas=asset_locations())

        self.soccer_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*self.buttonPos(0), *self.button_size),
            text="Soccer",
            manager=self,
            object_id=pygame_gui.core.ObjectID("soccer_button", "menu_button"),
        )
        self.addButtonEvent("soccer_button", lambda: self.playSim("soccer.yaml"))
        self._all_objs.append(self.soccer_button)

        soccer_settings_button_pos = [self.buttonPos(0)[0] + self.button_size[0] + 20, self.buttonPos(0)[1]]
        self.soccer_settings_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*soccer_settings_button_pos, *settings_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("soccer-settings", "settings_buttons"),
        )
        self.addButtonEvent("soccer-settings", self.clickSimSettings, "soccer.yaml")
        self.soccer_settings_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(
                *self.iconPos(soccer_settings_button_pos, settings_size, settings_icon_size), *settings_icon_size
            ),
            image_surface=pygame.image.load(settings_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("soccer-settings-icon"),
        )
        self._all_objs.append(self.soccer_settings_button)
        self._all_objs.append(self.soccer_settings_icon)
        soccer_bot_button_pos = [
            self.buttonPos(0)[0] + self.button_size[0] + settings_size[0] + 40,
            self.buttonPos(0)[1],
        ]
        self.soccer_bot_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*soccer_bot_button_pos, *bot_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("soccer-bot", "settings_buttons"),
        )
        self.addButtonEvent("soccer-bot", self.clickSimBots, "soccer.yaml")
        self.soccer_bot_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(soccer_bot_button_pos, bot_size, bot_icon_size), *bot_icon_size),
            image_surface=pygame.image.load(bot_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("soccer-bot-icon"),
        )
        self._all_objs.append(self.soccer_bot_button)
        self._all_objs.append(self.soccer_bot_icon)

        self.rescue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*self.buttonPos(1), *self.button_size),
            text="Rescue",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rescue_button", "menu_button"),
        )
        self.addButtonEvent("rescue_button", lambda: self.playSim("rescue.yaml"))
        self._all_objs.append(self.rescue_button)

        rescue_settings_button_pos = [self.buttonPos(1)[0] + self.button_size[0] + 20, self.buttonPos(1)[1]]
        self.rescue_settings_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*rescue_settings_button_pos, *settings_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rescue-settings", "settings_buttons"),
        )
        self.addButtonEvent("rescue-settings", self.clickSimSettings, "rescue.yaml")
        self.rescue_settings_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(
                *self.iconPos(rescue_settings_button_pos, settings_size, settings_icon_size), *settings_icon_size
            ),
            image_surface=pygame.image.load(settings_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rescue-settings-icon"),
        )
        self._all_objs.append(self.rescue_settings_button)
        self._all_objs.append(self.rescue_settings_icon)
        rescue_bot_button_pos = [
            self.buttonPos(1)[0] + self.button_size[0] + settings_size[0] + 40,
            self.buttonPos(1)[1],
        ]
        self.rescue_bot_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*rescue_bot_button_pos, *bot_size),
            text="",
            manager=self,
            object_id=pygame_gui.core.ObjectID("rescue-bot", "settings_buttons"),
        )
        self.addButtonEvent("rescue-bot", self.clickSimBots, "rescue.yaml")
        self.rescue_bot_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*self.iconPos(rescue_bot_button_pos, bot_size, bot_icon_size), *bot_icon_size),
            image_surface=pygame.image.load(bot_icon_path),
            manager=self,
            object_id=pygame_gui.core.ObjectID("rescue-bot-icon"),
        )
        self._all_objs.append(self.rescue_bot_button)
        self._all_objs.append(self.rescue_bot_icon)

        if self.show_custom:
            self.custom_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(*self.buttonPos(2), *self.button_size),
                text="Custom",
                manager=self,
                object_id=pygame_gui.core.ObjectID("custom_button", "menu_button"),
            )
            self.addButtonEvent("custom_button", self.clickCustom)
            self._all_objs.append(self.custom_button)

        self.bot_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*self.buttonPos(3 if self.show_custom else 2), *self.button_size),
            text="Bots",
            manager=self,
            object_id=pygame_gui.core.ObjectID("bots_button", "menu_button"),
        )
        self.addButtonEvent(
            "bots_button",
            lambda: ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BOTS),
        )
        self._all_objs.append(self.bot_button)

        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*self.buttonPos(4 if self.show_custom else 3), *self.button_size),
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
        super().generateObjects()

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
        self.slide_surface_prev = pygame.transform.smoothscale(self.slide_surface_prev, self._size)
        self.slide_surface_next = pygame.transform.smoothscale(self.slide_surface_next, self._size)
        self.slide_surface_prev.set_alpha(alpha_prev)
        self.slide_surface_next.set_alpha(alpha_next)
        bg_image.blit(self.slide_surface_prev, pygame.Rect(0, 0, *self._size))
        bg_image.blit(self.slide_surface_next, pygame.Rect(0, 0, *self._size))
        self.bg.set_image(bg_image)

    def clickSimSettings(self, preset):
        import importlib

        abs_path = find_abs(preset, allowed_areas=preset_locations())
        with open(abs_path, "r") as f:
            preset_config = yaml.safe_load(f)
        sim_path = find_abs(preset_config["sim_location"], allowed_areas=batch_locations())
        mname, cname = preset_config["visual_settings"].rsplit(".", 1)
        klass = getattr(importlib.import_module(mname), cname)
        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_SETTINGS,
            file=sim_path,
            settings=klass,
            allows_filename_change=False,
            extension="sim",
        )

    def clickSimBots(self, preset):
        abs_path = find_abs(preset, allowed_areas=preset_locations())
        with open(abs_path, "r") as f:
            preset_config = yaml.safe_load(f)
        sim_path = find_abs(preset_config["sim_location"], allowed_areas=batch_locations())
        ScreenObjectManager.instance.pushScreen(
            ScreenObjectManager.SCREEN_BOTS,
            batch_file=sim_path,
        )

    def clickCustom(self):
        ScreenObjectManager.instance.pushScreen(ScreenObjectManager.SCREEN_BATCH)

    def draw_ui(self, window_surface: pygame.surface.Surface):
        super().draw_ui(window_surface)

    def onPop(self):
        pass

    def initWithKwargs(self, **kwargs):
        super().initWithKwargs(**kwargs)
        self.slide_index = 0
        self.swapSlides()
