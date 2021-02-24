import pygame
import pygame_gui
from ev3sim.visual.animation_utils import rgb_to_hex


class BaseMenu(pygame_gui.UIManager):

    WINDOW_MODE_NORMAL = "normal"
    WINDOW_MODE_ERROR = "error"
    WINDOW_MODE_FILE = "file"

    def __init__(self, size, *args, **kwargs):
        self.window_mode = self.WINDOW_MODE_NORMAL
        self._size = size
        super().__init__(size, *args, **kwargs)
        self._all_objs = []
        self._button_events = []

    def addButtonEvent(self, id, event, *args, **kwargs):
        elem = (id, event, args, kwargs)
        for i in range(len(self._button_events)):
            if self._button_events[i][0] == id:
                # Overwrite if ID already exists.
                self._button_events[i] = elem
                break
        else:
            self._button_events.append(elem)

    def removeButtonEvent(self, id):
        to_remove = []
        for i in range(len(self._button_events)):
            if self._button_events[i][0] == id:
                to_remove.append(i)
        for idx in to_remove[::-1]:
            del self._button_events[idx]

    def setSize(self, size):
        self._size = size
        # Kinda sketch.
        self.set_window_resolution(size)
        self.root_container.set_dimensions(size)
        self.ui_window_stack.window_resolution = size

    def clearObjects(self):
        for obj in self._all_objs:
            obj.kill()
        self._all_objs = []
        self._button_events = []

    def generateObjects(self):
        if self.window_mode == self.WINDOW_MODE_ERROR:

            class ErrorWindow(pygame_gui.elements.UIWindow):
                def kill(self2):
                    self.window_mode = self.WINDOW_MODE_NORMAL
                    self.regenerateObjects()
                    return super().kill()

            dialog_size = (self._size[0] * 0.7, self._size[1] * 0.7)
            self.dialog = ErrorWindow(
                rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *dialog_size),
                manager=self,
                window_display_title="An error occured",
                object_id=pygame_gui.core.ObjectID("error_dialog"),
            )

            self.error_msg = pygame_gui.elements.UITextBox(
                relative_rect=pygame.Rect(20, 20, dialog_size[0] - 40, dialog_size[1] - 40),
                html_text=self.error_msg_text,
                manager=self,
                container=self.dialog,
                object_id=pygame_gui.core.ObjectID("error_msg", "text_dialog"),
            )
        if self.window_mode == self.WINDOW_MODE_FILE:

            class FileWindow(pygame_gui.windows.UIFileDialog):
                def kill(self2):
                    self.window_mode = self.WINDOW_MODE_NORMAL
                    self.regenerateObjects()
                    return super().kill()

            dialog_size = (self._size[0] * 0.7, self._size[1] * 0.7)
            self.dialog = FileWindow(
                rect=pygame.Rect(self._size[0] * 0.15, self._size[1] * 0.15, *dialog_size),
                manager=self,
                window_title=self.file_picker_title,
                object_id=pygame_gui.core.ObjectID("error_dialog"),
                initial_file_path=self.file_picker_path,
                allow_picking_directories=self.file_is_dir,
            )

    def addErrorDialog(self, msg):
        self.window_mode = self.WINDOW_MODE_ERROR
        self.error_msg_text = msg
        self.regenerateObjects()

    def addFileDialog(self, title, path, directory, onComplete):
        self.window_mode = self.WINDOW_MODE_FILE
        self.file_picker_title = title
        self.file_picker_path = path
        self.file_is_dir = directory
        self.file_on_complete = onComplete
        self.regenerateObjects()

    def regenerateObjects(self):
        self.clearObjects()
        self.generateObjects()

    def initWithKwargs(self, **kwargs):
        self.window_mode = self.WINDOW_MODE_NORMAL
        self.regenerateObjects()
        # Reset all animations
        self.animations = []

    def handleEvent(self, event, button_filter=lambda x: True):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for id, method, args, kwargs in self._button_events:
                if event.ui_object_id.split(".")[-1] == id and button_filter(id):
                    method(*args, **kwargs)
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            self.file_on_complete(event.text)

    def animateProperty(self, object, properties, start_values, end_values, rate_func, duration, dependent=None):
        """
        Animates object properties for a certain amount of time.
        dependent: the index of an animation to finish before this one starts.
        Returns the index of this animation.
        """
        if dependent == "follow":
            dependent = len(self.animations) - 1
        self.animations.append(
            {
                "object": object,
                "properties": properties,
                "start_values": start_values,
                "end_values": end_values,
                "rate_func": rate_func,
                "remaining": duration,
                "total": duration,
                "dependent": dependent,
            }
        )
        return len(self.animations) - 1

    def removeAnimation(self, index):
        for i in range(index + 1, len(self.animations)):
            if self.animations[i]["dependent"] == index:
                self.animations[i]["dependent"] = None
        for i in range(len(self.animations)):
            if self.animations[i]["dependent"] is not None and self.animations[i]["dependent"] > i:
                self.animations[i]["dependent"] -= 1
        self.animations = self.animations[:index] + self.animations[index + 1 :]

    colour_types = ("normal", "hovered", "active", "disabled", "selected")
    colour_ends = ("bg", "text", "border")

    def _setPropertyValue(self, object, properties, start_values, end_values, alpha):
        new_pos = None
        new_size = None
        requires_rebuild = False
        for property, start, end in zip(properties, start_values, end_values):
            if property == "position":
                new_pos = [s + (e - s) * alpha for s, e in zip(start, end)]
            if property == "dimensions":
                new_size = [s + (e - s) * alpha for s, e in zip(start, end)]
            if property in [f"{t}_{e}" for t in self.colour_types for e in self.colour_ends]:
                # For optimization purposes, start_v and end_v are rgb tuples, not hex strings.
                # TODO: Not sure if straight line interpolation in RGB space is the best approach.
                interp = [min(max(int(s + (e - s) * alpha), 0), 255) for s, e in zip(start, end)]
                object.colours[property] = pygame.Color(*interp)
                requires_rebuild = True
        if new_pos is not None:
            object.set_position(new_pos)
        if new_size is not None:
            object.set_dimensions(new_size)
        if requires_rebuild:
            object.rebuild()

    def update(self, time_delta: float):
        to_remove = []
        for i, anim in enumerate(self.animations):
            if anim["dependent"] is None:
                anim["remaining"] -= time_delta
                if anim["remaining"] < 0:
                    to_remove.append(i)
                    anim["remaining"] = 0
                self._setPropertyValue(
                    anim["object"],
                    anim["properties"],
                    anim["start_values"],
                    anim["end_values"],
                    anim["rate_func"](1 - anim["remaining"] / anim["total"]),
                )
        for idx in to_remove[::-1]:
            self.removeAnimation(idx)
        super().update(time_delta)
