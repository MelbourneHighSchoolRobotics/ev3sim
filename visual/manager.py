import pygame

class ScreenObjectManager:

    instance: 'ScreenObjectManager'

    screen: pygame.Surface
    screen_width: int
    screen_height: float

    def __init__(self, **kwargs):
        ScreenObjectManager.instance = self
        self.init_from_kwargs(**kwargs)

    def init_from_kwargs(self, **kwargs):
        self.screen_width = kwargs.get('screen_width', 640)
        self.screen_height = kwargs.get('screen_height', 480)

    def start_screen(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
