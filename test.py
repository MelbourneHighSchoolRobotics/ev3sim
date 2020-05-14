import pygame
from visual.manager import ScreenObjectManager
from visual.objects import Rectangle

man = ScreenObjectManager()
man.start_screen()

rect = Rectangle(height=0.15, width=0.3, stroke='#ff0000')

import numpy as np
import time

for x in np.arange(0, 6*np.pi, step=0.1):
    rect.rotation = x
    rect.position = (
        0.5 + np.cos(0.3*x) / 4,
        0.5 + np.sin(0.3*x) / 4,
        0
    )
    time.sleep(0.02)
    rect.apply_to_screen()
    pygame.display.update()
    man.screen.fill((0, 0, 0))

finished = False
while not finished:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            finished = True
