import pygame
import pygame_gui
from ev3sim.file_helper import find_abs, find_abs_directory
from ev3sim.search_locations import asset_locations


class SettingsVisualElement:

    num_objs = 0

    def __init__(self, json_keys, default_value, title, offset):
        self.offset = offset
        self.json_keys = json_keys
        self.default = default_value
        self.current = self.default
        self.title = title
        self.menu = None

    def set_menu(self, menu):
        self.menu = menu

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
            if key not in cur:
                cur[key] = {}
            cur = cur[key]
        cur[self.json_keys[-1]] = self.current

    def generateVisual(self, size, container, manager, idx):
        raise NotImplementedError()


class Button(SettingsVisualElement):

    num_objs = 1

    def __init__(self, title, offset, onClick):
        self.title = title
        self.offset = offset
        self.menu = None
        self.onClick = onClick
        # We want the filename in current.
        self.json_keys = "__filename__"

    def getFromJson(self, json_obj):
        pass

    def setToJson(self, json_obj):
        pass

    def generateVisual(self, size, container, manager, idx):
        self.container = container
        off = self.offset(size)
        if size[0] < 540:
            button_size = (size[0] - 40, 40)
            button_pos = (off[0] + 20, off[1])
        else:
            button_size = ((size[0] - 40) * 0.5 - 20, 40)
            button_pos = (off[0] + 30, off[1])
        self.button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*button_pos, *button_size),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-button", "option-button"),
            container=container,
            text=self.title,
        )
        return [self.button]

    def handlePressed(self, idx):
        assert idx == 0, f"{idx} expected to be 0."
        if self.onClick is not None:
            self.onClick(self.current)


class FileEntry(SettingsVisualElement):

    num_objs = 4

    def __init__(self, json_keys, default_value, is_directory, relative_paths, title, offset):
        super().__init__(json_keys, default_value, title, offset)
        self.is_directory = is_directory
        self.relative_paths = relative_paths

    def generateVisual(self, size, container, manager, idx):
        self.container = container
        off = self.offset(size)

        label_size = ((size[0] - 40) / 2 - 10, 40)
        label_pos = (off[0] + 20, off[1])
        label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(*label_pos, *label_size),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-file-label", "entry-label"),
            container=container,
            text=self.title,
        )

        button_size = ((size[0] - 40) * 0.25 - 20, 44)
        button_size = [min(button_size[0], button_size[1])] * 2
        file_size = ((size[0] - 40) / 2 - button_size[0] - 30, 40)
        button_pos = (
            off[0] + 50 + label_size[0] + file_size[0],
            off[1] - 2,
        )
        file_pos = (off[0] + 40 + label_size[0], off[1])
        click = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(*button_pos, *button_size),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+2}-button", "file-button"),
            container=container,
            text="",
        )
        img = pygame.image.load(find_abs("ui/folder.png", allowed_areas=asset_locations()))
        if img.get_size() != button_size:
            img = pygame.transform.smoothscale(img, button_size)
        click_icon = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(*button_pos, *button_size),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+3}-image", "file-image"),
            container=container,
            image_surface=img,
        )

        self.filename = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(*file_pos, *file_size),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+1}-file-name", "entry-label"),
            container=container,
            text=self.current if self.current else "",
        )

        return [label, self.filename, click, click_icon]

    def handlePressed(self, idx):
        assert idx == 2, f"{idx} expected to be 2."

        def onComplete(path):
            if self.is_directory:
                if not path:
                    return
                self.current = path
                self.filename.set_text(self.current)
                return
            if not path:
                return
            for pathname in self.relative_paths:
                dirpath = find_abs_directory(pathname, create=True)
                if path.startswith(dirpath):
                    actual_path = path[len(dirpath) :]
                    break
            else:
                msg = '<font color="#DD4045">This file must be contained in one of the following directories:</font>'
                for pathname in self.relative_paths:
                    dirpath = find_abs_directory(pathname, create=True)
                    msg = msg + "<br><br>" + dirpath
                msg = msg + "</font>"
                self.menu.addErrorDialog(msg)
                return
            self.current = actual_path
            self.filename.set_text(self.current)

        import platform

        if platform.system() == "Windows":
            from os.path import join
            from tkinter import Tk
            from tkinter.filedialog import askdirectory, askopenfilename

            Tk().withdraw()
            if self.is_directory:
                path = askdirectory()
            else:
                path = join(askopenfilename())
            onComplete(path)
        else:
            self.menu.addFileDialog(
                "Select " + self.title,
                find_abs_directory(self.relative_paths[0], create=True) if self.relative_paths else None,
                self.is_directory,
                onComplete,
            )


class TextEntry(SettingsVisualElement):
    def setToJson(self, json_obj):
        self.current = self.obj.text
        super().setToJson(json_obj)

    def getEntryRect(self, off):
        if self.title is None:
            entry_size = ((self.size[0] - 40) - 20, 60)
            entry_pos = (
                off[0] + 20,
                off[1],
            )
        else:
            entry_size = ((self.size[0] - 40) / 2 - 20, 60)
            entry_pos = (
                off[0] + 20 + (self.size[0] - 40) / 2 + 10,
                off[1],
            )
        return pygame.Rect(*entry_pos, *entry_size)

    def getLabelRect(self, off):
        label_size = ((self.size[0] - 40) / 2 - 20, 40)
        label_pos = off[0] + 20, off[1]
        return pygame.Rect(*label_pos, *label_size)

    def generateVisual(self, size, container, manager, idx):
        self.size = size
        self.num_objs = 0
        self.container = container
        off = self.offset(size)
        self.obj = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.getEntryRect(off),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-text"),
            container=container,
        )
        self.obj.set_text(str(self.current))
        self.num_objs += 1

        if self.title is not None:
            self.num_objs += 1
            obj2 = pygame_gui.elements.UILabel(
                relative_rect=self.getLabelRect(off),
                manager=manager,
                object_id=pygame_gui.core.ObjectID(f"{idx+1}-text-label", "entry-label"),
                container=container,
                text=self.title,
            )
            return [self.obj, obj2]
        return [self.obj]


class NumberEntry(TextEntry):
    def __init__(self, json_keys, default_value, title, offset, conversion):
        self.conversion = conversion
        super().__init__(json_keys, default_value, title, offset)

    def setToJson(self, json_obj):
        self.current = self.conversion(self.obj.text)
        SettingsVisualElement.setToJson(self, json_obj)

    def getEntryRect(self, off):
        if self.size[0] < 540:
            entry_size = ((self.size[0] - 40) * 0.25 - 20, 60)
            entry_pos = (
                off[0] + self.container.relative_rect.left + 20 + (self.size[0] - 40) * 0.75 + 10,
                off[1] + self.container.relative_rect.top,
            )
        else:
            entry_size = ((self.size[0] - 40) * 0.125 - 20, 60)
            entry_pos = (
                off[0] + self.container.relative_rect.left + 20 + (self.size[0] - 40) * 0.375 + 10,
                off[1] + self.container.relative_rect.top,
            )
        return pygame.Rect(*entry_pos, *entry_size)

    def getLabelRect(self, off):
        if self.size[0] < 540:
            label_size = ((self.size[0] - 40) * 0.75 - 20, 40)
            label_pos = (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
        else:
            label_size = ((self.size[0] - 40) * 0.375 - 20, 40)
            label_pos = (off[0] + self.container.relative_rect.left + 20, off[1] + self.container.relative_rect.top)
        return pygame.Rect(*label_pos, *label_size)


class Checkbox(SettingsVisualElement):

    num_objs = 3

    def handlePressed(self, idx):
        assert idx == 0, f"{idx} expected to be 0."
        self.current = not self.current
        self.setCheckboxBg(self.current, self.obj3)

    def getLabelRect(self, off):
        if self.size[0] < 540:
            button_size = ((self.size[0] - 40) * 0.25 - 20, 45)
            button_size = [min(button_size[0], button_size[1])] * 2
            label_size = ((self.size[0] - 40) - 20 - button_size[0], 40)
            label_pos = (off[0] + 20, off[1])
        else:
            button_size = ((self.size[0] - 40) * 0.125 - 20, 45)
            button_size = [min(button_size[0], button_size[1])] * 2
            label_size = ((self.size[0] - 40) * 0.5 - 20 - button_size[0], 40)
            label_pos = (off[0] + 20, off[1])
        return pygame.Rect(*label_pos, *label_size)

    def getCheckRect(self, off):
        if self.size[0] < 540:
            button_size = ((self.size[0] - 40) * 0.25 - 20, 45)
            button_size = [min(button_size[0], button_size[1])] * 2
            btn_pos = (
                off[0] + 20 + (self.size[0] - 40) + 10 - button_size[0],
                off[1],
            )
        else:
            button_size = ((self.size[0] - 40) * 0.125 - 20, 45)
            button_size = [min(button_size[0], button_size[1])] * 2
            btn_pos = (
                off[0] + 20 + (self.size[0] - 40) * 0.5 - button_size[0] - 10,
                off[1],
            )
        return pygame.Rect(*btn_pos, *button_size)

    def generateVisual(self, size, container, manager, idx):
        self.size = size
        self.container = container
        off = self.offset(size)
        obj2 = pygame_gui.elements.UILabel(
            relative_rect=self.getLabelRect(off),
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx+1}-button-label", "entry-label"),
            container=container,
            text=self.title,
        )
        check_rect = self.getCheckRect(off)
        self.obj3 = pygame_gui.elements.UIImage(
            relative_rect=check_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID("check-image"),
            container=container,
            image_surface=pygame.Surface((check_rect.width, check_rect.height)),
        )
        self.setCheckboxBg(self.current, self.obj3)
        obj = pygame_gui.elements.UIButton(
            relative_rect=check_rect,
            manager=manager,
            object_id=pygame_gui.core.ObjectID(f"{idx}-button", "checkbox-button"),
            container=container,
            text="",
        )
        self.setCheckboxBg(self.current, self.obj3)
        return [obj, obj2, self.obj3]

    def setCheckboxBg(self, value, obj):
        img = pygame.image.load(
            find_abs("ui/box_check.png" if value else "ui/box_clear.png", allowed_areas=asset_locations())
        )
        if img.get_size() != obj.rect.size:
            img = pygame.transform.smoothscale(img, (obj.rect.width, obj.rect.height))
        obj.set_image(img)
