import os
import pygame
import pygame_gui
import yaml
from ev3sim.file_helper import find_abs_directory
from ev3sim.visual.menus.base_menu import BaseMenu


class SettingsMenu(BaseMenu):
    # TODO: Make this scroll. Maybe fix the height of save/cancel to bottom.

    onSave = None
    onCancel = None

    def clearEvents(self):
        self.onSave = None
        self.onCancel = None

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
                if obj.json_keys == "__filename__" and not self.allows_filename_change:
                    obj.obj.disable()
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
            text="Create" if self.creating else "Save",
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
                        if obj.json_keys == "__filename__":
                            if self.creating:
                                # Make sure the name can be used.
                                creation_dir = find_abs_directory(self.creation_area, create=True)
                                current_filepath = os.path.join(creation_dir, f"{obj.obj.text}.yaml")
                                rel_file = f"{obj.obj.text}.yaml"
                                if os.path.exists(current_filepath):
                                    raise ValueError("A file with this name already exists.")
                            else:
                                # Make sure the name can be used.
                                end, front = os.path.split(self.filename)
                                current_filepath = os.path.join(end, f"{obj.obj.text}.yaml")
                                if current_filepath != self.filename and os.path.exists(current_filepath):
                                    raise ValueError("A file with this name already exists.")
                                if current_filepath != self.filename:
                                    # Remove the previous file.
                                    os.remove(self.filename)
                        else:
                            obj.setToJson(json_obj)
                string = yaml.dump(json_obj)
                with open(current_filepath, "w") as f:
                    f.write(string)
                from ev3sim.visual.manager import ScreenObjectManager

                ScreenObjectManager.instance.popScreen()
                if self.onSave is not None:
                    self.onSave(rel_file)
            elif event.ui_object_id == "cancel-changes":
                from ev3sim.visual.manager import ScreenObjectManager

                ScreenObjectManager.instance.popScreen()
                if self.onCancel is not None:
                    self.onCancel()

    def onPop(self):
        pass

    def initWithKwargs(self, **kwargs):
        # kwargs[file] = file these settings are changing
        # kwargs[settings] = list of settings groups
        import os

        self.creating = kwargs.get("creating", False)
        # The relative directory to create the file in.
        self.creation_area = kwargs.get("creation_area", "")
        self.allows_filename_change = kwargs.get("allows_filename_change", self.creating)
        # If creating a new thing, what data do you start with.
        self.starting_data = kwargs.get("starting_data", {})
        self.settings_obj = kwargs["settings"]
        if not self.creating:
            self.filename = kwargs["file"]
            with open(self.filename, "r") as f:
                json_obj = yaml.safe_load(f)
            for group in self.settings_obj:
                for obj in group["objects"]:
                    if obj.json_keys == "__filename__":
                        __, show_name = os.path.split(self.filename)
                        show_name = show_name.rstrip(".yaml")
                        obj.current = show_name
                    else:
                        obj.getFromJson(json_obj)

        super().initWithKwargs(**kwargs)
