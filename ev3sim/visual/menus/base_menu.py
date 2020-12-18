import pygame
import pygame_gui


class BaseMenu(pygame_gui.UIManager):
    def __init__(self, size, *args, **kwargs):
        self._size = size
        super().__init__(size, *args, **kwargs)
        self._all_objs = []
        self._button_events = []

    def addButtonEvent(self, id, event, *args, **kwargs):
        self._button_events.append(
            (
                id,
                event,
                args,
                kwargs,
            )
        )

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
        raise NotImplementedError()

    def sizeObjects(self):
        raise NotImplementedError()

    def regenerateObjects(self):
        self.clearObjects()
        self.generateObjects()
        self.sizeObjects()

    def initWithKwargs(self, **kwargs):
        self.regenerateObjects()

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for id, method, args, kwargs in self._button_events:
                if event.ui_object_id.split(".")[-1] == id:
                    method(*args, **kwargs)
