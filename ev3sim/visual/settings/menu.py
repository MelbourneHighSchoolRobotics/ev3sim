import pygame
import pygame_gui
import yaml
from ev3sim.visual.menus.base_menu import BaseMenu


class SettingsMenu(BaseMenu):
    # TODO: Make this scroll. Maybe fix the height of save/cancel to bottom.

    def sizeObjects(self):
        yPadding = 20
        yOffset = 0
        index = 0
        for group in self.settings_obj:
            yOffset += yPadding
            self._all_objs[index].set_dimensions((self._size[0] - 40, group["height"](self._size)))
            self._all_objs[index].set_position((20, yOffset))
            index += 1
            for obj in group["objects"]:
                obj.resize(self._all_objs, index)
                index += obj.num_objs
            yOffset += group["height"](self._size)
        yOffset += yPadding
        self.bg.set_dimensions(self._size)
        index += 1
        self._all_objs[index].set_dimensions((self._size[0] - 40, 80))
        self._all_objs[index].set_position((20, yOffset))
        index += 1
        self.save.set_dimensions((120, 60))
        self.save.set_position((self._size[0] - 300, yOffset + 10))
        index += 1
        self.cancel.set_dimensions((120, 60))
        self.cancel.set_position((self._size[0] - 160, yOffset + 10))
        index += 1

    def generateObjects(self):
        dummy_rect = pygame.Rect(0, 0, *self._size)
        index = 0
        for group in self.settings_obj:
            container = pygame_gui.elements.UIPanel(
                relative_rect=dummy_rect,
                starting_layer_height=-1,
                manager=self,
                object_id=pygame_gui.core.ObjectID(f"{index}-bg", "settings-background"),
            )
            self._all_objs.append(container)
            index += 1
            for obj in group["objects"]:
                for obj2 in obj.generateVisual(dummy_rect, container, self, index):
                    self._all_objs.append(obj2)
                index += obj.num_objs
        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-2,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)
        index += 1
        container = pygame_gui.elements.UIPanel(
            relative_rect=dummy_rect,
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID(f"{index}-bg", "settings-background"),
        )
        self._all_objs.append(container)
        index += 1
        self.save = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("save-changes", "action_button"),
            text="Save",
        )
        self._all_objs.append(self.save)
        index += 1
        self.cancel = pygame_gui.elements.UIButton(
            relative_rect=dummy_rect,
            manager=self,
            object_id=pygame_gui.core.ObjectID("cancel-changes", "action_button"),
            text="Cancel",
        )
        self._all_objs.append(self.cancel)
        index += 1

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            obj_id = event.ui_object_id.split(".")[-1].split("-")[0]
            if obj_id.isnumeric():
                idx = int(obj_id)
                index = 0
                for group in self.settings_obj:
                    index += 1
                    for obj in group["objects"]:
                        if index + obj.num_objs > idx:
                            obj.handlePressed(idx - index)
                            return
                        index += obj.num_objs
            # Not one of the dynamic buttons, save or cancel.
            if event.ui_object_id == "save-changes":
                with open(self.filename, "r") as f:
                    json_obj = yaml.safe_load(f)
                for group in self.settings_obj:
                    for obj in group["objects"]:
                        obj.setToJson(json_obj)
                string = yaml.dump(json_obj)
                with open(self.filename, "w") as f:
                    f.write(string)
                from ev3sim.visual.manager import ScreenObjectManager

                ScreenObjectManager.instance.popScreen()
            elif event.ui_object_id == "cancel-changes":
                from ev3sim.visual.manager import ScreenObjectManager

                ScreenObjectManager.instance.popScreen()

    def onPop(self):
        pass

    def initWithKwargs(self, **kwargs):
        # kwargs[file] = file these settings are changing
        # kwargs[settings] = list of settings groups
        self.filename = kwargs["file"]
        with open(self.filename, "r") as f:
            json_obj = yaml.safe_load(f)
        self.settings_obj = kwargs["settings"]
        for group in self.settings_obj:
            for obj in group["objects"]:
                obj.getFromJson(json_obj)
        super().initWithKwargs(**kwargs)
