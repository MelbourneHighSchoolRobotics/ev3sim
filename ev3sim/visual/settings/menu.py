from ev3sim.settings import SettingsManager
from ev3sim.visual.settings.elements import TextEntry
import os
import pygame
import pygame_gui
import yaml
from ev3sim.file_helper import find_abs_directory
from ev3sim.visual.menus.base_menu import BaseMenu


class SettingsMenu(BaseMenu):

    onSave = None
    onCancel = None

    MODE_NORMAL = "normal"
    MODE_ERROR = "error"

    def clearEvents(self):
        self.onSave = None
        self.onCancel = None

    def generateObjects(self):
        yPadding = 20
        yOffset = 0
        index = 0
        for group in self.settings_obj:
            yOffset += yPadding
            container = pygame_gui.elements.UIPanel(
                relative_rect=pygame.Rect(0, 0, *self._size),
                starting_layer_height=-1,
                manager=self,
                object_id=pygame_gui.core.ObjectID(f"{index}-bg", "settings-background"),
            )
            self._all_objs.append(container)
            index += 1
            for obj in group["objects"]:
                obj.set_menu(self)
                for obj2 in obj.generateVisual(
                    (self._size[0] - 40, group["height"](self._size)), container, self, index
                ):
                    self._all_objs.append(obj2)
                if obj.json_keys == "__filename__" and not self.allows_filename_change:
                    if isinstance(obj, TextEntry):
                        obj.obj.disable()
                index += obj.num_objs
            container.set_position((20, yOffset))
            container.set_dimensions((self._size[0] - 40, group["height"](self._size)))
            yOffset += group["height"](self._size)
        yOffset += yPadding

        self.bg = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, *self._size),
            starting_layer_height=-2,
            manager=self,
            object_id=pygame_gui.core.ObjectID("background"),
        )
        self._all_objs.append(self.bg)

        container = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(20, yOffset, self._size[0] - 40, 80),
            starting_layer_height=-1,
            manager=self,
            object_id=pygame_gui.core.ObjectID(f"{index}-bg", "settings-background"),
        )
        self._all_objs.append(container)

        self.save = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self._size[0] - 300, yOffset + 10, 120, 60),
            manager=self,
            object_id=pygame_gui.core.ObjectID("save-changes", "action_button"),
            text="Create" if self.creating else "Save",
        )
        self.addButtonEvent("save-changes", self.clickSave)
        self._all_objs.append(self.save)

        self.cancel = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self._size[0] - 160, yOffset + 10, 120, 60),
            manager=self,
            object_id=pygame_gui.core.ObjectID("cancel-changes", "action_button"),
            text="Cancel",
        )
        self.addButtonEvent("cancel-changes", self.clickCancel)
        self._all_objs.append(self.cancel)
        super().generateObjects()

    def handleEvent(self, event):
        super().handleEvent(event)
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

    def clickSave(self):
        if not self.creating:
            with open(self.filename, "r") as f:
                json_obj = yaml.safe_load(f)
        else:
            json_obj = self.starting_data
        current_filepath = None
        rel_file = None
        if not self.creating:
            current_filepath = self.filename
        for group in self.settings_obj:
            for obj in group["objects"]:
                if obj.json_keys == "__filename__" and isinstance(obj, TextEntry):
                    if self.creating:
                        # Make sure the name can be used.
                        creation_dir = find_abs_directory(self.creation_area, create=True)
                        current_filepath = os.path.join(creation_dir, f"{obj.obj.text}.{self.extension}")
                        rel_file = f"{obj.obj.text}.{self.extension}"
                        if os.path.exists(current_filepath):
                            self.addErrorDialog('<font color="#DD4045">A file with this name already exists.</font>')
                            return False
                    else:
                        # Make sure the name can be used.
                        end, front = os.path.split(self.filename)
                        current_filepath = os.path.join(end, f"{obj.obj.text}.{self.extension}")
                        if current_filepath != self.filename and os.path.exists(current_filepath):
                            self.addErrorDialog('<font color="#DD4045">A file with this name already exists.</font>')
                            return False
                        if current_filepath != self.filename:
                            # Remove the previous file.
                            os.remove(self.filename)
                else:
                    obj.setToJson(json_obj)
                    try:
                        # If we are editing loaded settings, then apply the changes.
                        settings = {}
                        cur = settings
                        prev = None
                        for key in obj.json_keys:
                            cur[key] = {}
                            prev = cur
                            cur = cur[key]
                        prev[obj.json_keys[-1]] = obj.current
                        SettingsManager.instance.setMany(settings)
                    except:
                        pass
        string = yaml.dump(json_obj)
        with open(current_filepath, "w") as f:
            f.write(string)
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.popScreen()
        if self.onSave is not None:
            self.onSave(rel_file)
        return True

    def clickCancel(self):
        from ev3sim.visual.manager import ScreenObjectManager

        if self.onCancel is not None:
            self.onCancel()
        ScreenObjectManager.instance.popScreen()

    def onPop(self):
        pass

    def initWithKwargs(self, **kwargs):
        # kwargs[file] = file these settings are changing
        # kwargs[settings] = list of settings groups
        import os

        self.mode = self.MODE_NORMAL
        self.creating = kwargs.get("creating", False)
        # The relative directory to create the file in.
        self.creation_area = kwargs.get("creation_area", "")
        self.allows_filename_change = kwargs.get("allows_filename_change", self.creating)
        # If creating a new thing, what data do you start with.
        self.starting_data = kwargs.get("starting_data", {})
        self.settings_obj = kwargs["settings"]
        # Different files have different extensions to add
        self.extension = kwargs.get("extension", "yaml")
        if not self.creating:
            self.filename = kwargs["file"]
            with open(self.filename, "r") as f:
                json_obj = yaml.safe_load(f)
            for group in self.settings_obj:
                for obj in group["objects"]:
                    if obj.json_keys == "__filename__":
                        __, show_name = os.path.split(self.filename)
                        show_name = show_name[: -(len(f".{self.extension}"))]
                        obj.current = show_name
                    else:
                        obj.getFromJson(json_obj)

        super().initWithKwargs(**kwargs)
