import pygame
import pygame_gui


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

    def handleEvent(self, event, button_filter=lambda x: True):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for id, method, args, kwargs in self._button_events:
                if event.ui_object_id.split(".")[-1] == id and button_filter(id):
                    method(*args, **kwargs)
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            self.file_on_complete(event.text)
