import pygame_gui


class BaseMenu(pygame_gui.UIManager):
    def __init__(self, size, *args, **kwargs):
        self._size = size
        super().__init__(size, *args, **kwargs)
        self._all_objs = []

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

    def generateObjects(self):
        raise NotImplementedError()

    def sizeObjects(self):
        raise NotImplementedError()

    def initWithKwargs(self, **kwargs):
        self.clearObjects()
        self.generateObjects()
        self.sizeObjects()
