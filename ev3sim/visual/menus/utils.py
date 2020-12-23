import pygame, pygame_gui


class CustomScroll(pygame_gui.elements.UIScrollingContainer):
    """This is very hacky but the pygame_gui Scrolling Container doesn't seem much better/extensible :/"""

    cur_y = 0
    # How many elements are we containing?
    num_elems = 0
    # What is the size of an element?
    elems_size = 90
    # How many elements should we see at once?
    span_elems = 5

    def _check_scroll_bars_and_adjust(self):
        super()._check_scroll_bars_and_adjust()
        return False, False

    def process_event(self, event: pygame.event.Event) -> bool:
        consumed_event = False

        if self.is_enabled and event.type == pygame.MOUSEWHEEL:
            self.cur_y += event.y * 10
            self.cur_y = min(0, max(self.cur_y, -self.elems_size * (self.num_elems - self.span_elems)))
            if event.y != 0:
                self.set_scroll(self.cur_y)
                consumed_event = True
        return consumed_event and super().process_event(event)

    def set_scroll(self, y):
        self.scrollable_container.set_relative_position((self.scrollable_container.relative_rect.x, y))
