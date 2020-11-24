from ev3sim.file_helper import find_abs
import pygame
import pygame_gui


class SettingsVisualElement:

    num_objs = 0

    def __init__(self, json_keys, default_value, title, offset):
        self.offset = offset
        self.json_keys = json_keys
        self.default = default_value
        self.current = self.default
        self.title = title

    def getFromJson(self, json_obj):
        try:
            cur = json_obj
            for key in self.json_keys:
                cur = cur[key]
            self.current = cur
        except:
            # It's ok if we don't already have this setting.
            pass

    def setToJson(self, json_obj):
        cur = json_obj
        for key in self.json_keys[:-1]:
            cur = cur[key]
        cur[self.json_keys[-1]] = self.current

    def resize(self, objects, index):
        raise NotImplementedError()

    def generateVisual(self, relative_rect, container, manager, idx):
        raise NotImplementedError()


class FileEntry(SettingsVisualElement):

    num_objs = 4

    def generateVisual(self, relative_rect, container, manager, idx):
        self.container = container
        label = pygame_gui.elements.UILabel(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-file-label", "entry-label"),
            container=container,
            text=self.title,
        )
        self.filename = pygame_gui.elements.UILabel(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+1}-file-name", "entry-label"),
            container=container,
            text=self.current,
        )
        click = pygame_gui.elements.UIButton(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+2}-button", "file-button"),
            container=container,
            text="",
        )
        click_icon = pygame_gui.elements.UIImage(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+3}-image", "file-image"),
            container=container,
            image_surface=pygame.Surface((relative_rect.width, relative_rect.height)),
        )
        return [label, self.filename, click, click_icon]

    def resize(self, objs, index):
        off = self.offset((self.container.relative_rect.width, self.container.relative_rect.height))
        button_size = ((self.container.relative_rect.width - 40) * 0.25 - 20, 44)
        button_size = [min(button_size[0], button_size[1])] * 2
        label_size = ((self.container.relative_rect.width - 40) / 2 - 10, 40)
        file_size = ((self.container.relative_rect.width - 40) / 2 - button_size[0] - 30, 40)
        objs[index].set_dimensions(label_size)
        objs[index+1].set_dimensions(file_size)
        objs[index+2].set_dimensions(button_size)
        objs[index+3].set_dimensions(button_size)

        objs[index].set_position(
            (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
        )
        objs[index + 1].set_position(
            (off[0] + self.container.relative_rect.left + 40 + label_size[0], off[1] + self.container.relative_rect.top)
        )
        objs[index + 2].set_position(
            (off[0] + self.container.relative_rect.left + 50 + label_size[0] + file_size[0], off[1] + self.container.relative_rect.top - 2)
        )
        objs[index + 3].set_position(
            (off[0] + self.container.relative_rect.left + 50 + label_size[0] + file_size[0], off[1] + self.container.relative_rect.top - 2)
        )
        img = pygame.image.load(
            find_abs("ui/folder.png", allowed_areas=["package/assets/"])
        )
        if img.get_size() != objs[index + 3].rect.size:
            img = pygame.transform.smoothscale(img, (objs[index + 3].rect.width, objs[index + 3].rect.height))
        objs[index + 3].set_image(img)

    def handlePressed(self, idx):
        assert idx == 2, f"{idx} expected to be 2."
        # Open file dialog.
        from tkinter import Tk
        from tkinter.filedialog import askdirectory

        Tk().withdraw()
        directory = askdirectory()
        self.current = directory
        self.filename.set_text(self.current)

class TextEntry(SettingsVisualElement):

    num_objs = 2

    def setToJson(self, json_obj):
        self.current = self.obj.text
        super().setToJson(json_obj)

    def generateVisual(self, relative_rect, container, manager, idx):
        self.container = container
        self.obj = pygame_gui.elements.UITextEntryLine(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-text"),
            container=container,
        )
        self.obj.set_text(str(self.current))
        obj2 = pygame_gui.elements.UILabel(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+1}-text-label", "entry-label"),
            container=container,
            text=self.title,
        )
        return [self.obj, obj2]

    def resize(self, objs, index):
        off = self.offset((self.container.relative_rect.width, self.container.relative_rect.height))
        objs[index].set_dimensions(((self.container.relative_rect.width - 40) / 2 - 20, 60))
        objs[index + 1].set_dimensions(((self.container.relative_rect.width - 40) / 2 - 20, 40))
        objs[index].set_position(
            (
                off[0] + self.container.relative_rect.left + 20 + (self.container.relative_rect.width - 40) / 2 + 10,
                off[1] + self.container.relative_rect.top,
            )
        )
        objs[index + 1].set_position(
            (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
        )


class NumberEntry(TextEntry):
    def setToJson(self, json_obj):
        self.current = int(self.obj.text)
        SettingsVisualElement.setToJson(self, json_obj)

    def resize(self, objs, index):
        off = self.offset((self.container.relative_rect.width, self.container.relative_rect.height))
        if self.container.relative_rect.width < 540:
            objs[index].set_dimensions(((self.container.relative_rect.width - 40) * 0.25 - 20, 60))
            objs[index + 1].set_dimensions(((self.container.relative_rect.width - 40) * 0.75 - 20, 40))
            objs[index].set_position(
                (
                    off[0]
                    + self.container.relative_rect.left
                    + 20
                    + (self.container.relative_rect.width - 40) * 0.75
                    + 10,
                    off[1] + self.container.relative_rect.top,
                )
            )
            objs[index + 1].set_position(
                (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
            )
        else:
            objs[index].set_dimensions(((self.container.relative_rect.width - 40) * 0.125 - 20, 60))
            objs[index + 1].set_dimensions(((self.container.relative_rect.width - 40) * 0.375 - 20, 40))
            objs[index].set_position(
                (
                    off[0]
                    + self.container.relative_rect.left
                    + 20
                    + (self.container.relative_rect.width - 40) * 0.375
                    + 10,
                    off[1] + self.container.relative_rect.top,
                )
            )
            objs[index + 1].set_position(
                (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
            )


class Checkbox(SettingsVisualElement):

    num_objs = 3

    def handlePressed(self, idx):
        assert idx == 0, f"{idx} expected to be 0."
        self.current = not self.current
        self.setCheckboxBg(self.current, self.obj3)

    def generateVisual(self, relative_rect, container, manager, idx):
        self.container = container
        obj2 = pygame_gui.elements.UILabel(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+1}-button-label", "entry-label"),
            container=container,
            text=self.title,
        )
        self.obj3 = pygame_gui.elements.UIImage(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID("check-image"),
            container=container,
            image_surface=pygame.Surface((relative_rect.width, relative_rect.height)),
        )
        self.setCheckboxBg(self.current, self.obj3)
        obj = pygame_gui.elements.UIButton(
            relative_rect=relative_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-button", "checkbox-button"),
            container=container,
            text="",
        )
        return [obj, obj2, self.obj3]

    def setCheckboxBg(self, value, obj):
        img = pygame.image.load(
            find_abs("ui/box_check.png" if value else "ui/box_clear.png", allowed_areas=["package/assets/"])
        )
        if img.get_size() != obj.rect.size:
            img = pygame.transform.smoothscale(img, (obj.rect.width, obj.rect.height))
        obj.set_image(img)

    def resize(self, objs, index):
        off = self.offset((self.container.relative_rect.width, self.container.relative_rect.height))
        if self.container.relative_rect.width < 540:
            button_size = ((self.container.relative_rect.width - 40) * 0.25 - 20, 45)
            button_size = [min(button_size[0], button_size[1])] * 2
            objs[index].set_dimensions(button_size)
            objs[index + 2].set_dimensions(button_size)
            objs[index + 1].set_dimensions(((self.container.relative_rect.width - 40) - 20 - button_size[0], 40))
            objs[index].set_position(
                (
                    off[0]
                    + self.container.relative_rect.left
                    + 20
                    + (self.container.relative_rect.width - 40)
                    + 10
                    - button_size[0],
                    off[1] + self.container.relative_rect.top,
                )
            )
            objs[index + 2].set_position(
                (
                    off[0]
                    + self.container.relative_rect.left
                    + 20
                    + (self.container.relative_rect.width - 40)
                    + 10
                    - button_size[0],
                    off[1] + self.container.relative_rect.top,
                )
            )
            objs[index + 1].set_position(
                (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
            )
        else:
            button_size = ((self.container.relative_rect.width - 40) * 0.125 - 20, 45)
            button_size = [min(button_size[0], button_size[1])] * 2
            objs[index].set_dimensions(button_size)
            objs[index + 2].set_dimensions(button_size)
            objs[index + 1].set_dimensions(((self.container.relative_rect.width - 40) * 0.5 - 20 - button_size[0], 40))
            objs[index].set_position(
                (
                    off[0]
                    + self.container.relative_rect.left
                    + 20
                    + (self.container.relative_rect.width - 40) * 0.5
                    - button_size[0]
                    - 10,
                    off[1] + self.container.relative_rect.top,
                )
            )
            objs[index + 2].set_position(
                (
                    off[0]
                    + self.container.relative_rect.left
                    + 20
                    + (self.container.relative_rect.width - 40) * 0.5
                    - button_size[0]
                    - 10,
                    off[1] + self.container.relative_rect.top,
                )
            )
            objs[index + 1].set_position(
                (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
            )
        self.setCheckboxBg(self.current, objs[index + 2])
