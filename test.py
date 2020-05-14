# This is TEMPORARY
import pygame
from visual.manager import ScreenObjectManager
from visual.objects import Rectangle

man = ScreenObjectManager()
man.start_screen()

rect = Rectangle(height=0.15, width=0.3, stroke='#ff0000')
rect2 = Rectangle(height=0.15, width=0.3, fill='#00ff00', stroke='#0000ff')
man.registerObject(rect, 'testingRect')
man.registerObject(rect2, 'testingRect2')


import numpy as np
import time

for x in np.arange(0, 6*np.pi, step=0.1):
    rect.rotation = x
    rect.position = (
        0.5 + np.cos(0.3*x) / 4,
        0.5 + np.sin(0.3*x) / 4,
        1
    )
    rect2.rotation = x + np.pi / 2
    rect2.position = (
        0.5 + np.cos(0.3*x) / 4,
        0.5 + np.sin(0.3*x) / 4,
        0
    )
    man.applyToScreen()
    time.sleep(0.02)

finished = False
while not finished:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            finished = True
