class IInteractor:
    """
    An interactor can be thought of as a robot in the simulation which has much more access to the inner workings of the system, and no physical presence.

    Any actions or dynamic elements in the soccer simulation is due to `interactors`. You can find the location of these interactors in `presets/soccer.yaml`.
    """

    constants: dict

    def __init__(self, **kwargs):
        pass

    def startUp(self):
        """Called when the interactor is instantiated (After elements are spawned in, but before any ticks are done)."""
        pass

    def tick(self, tick) -> bool:
        """
        Called once every tick in the simulation.

        :param int tick: The number of ticks since epoch.

        :returns bool: If ``True`` is returned, this interactor is assumed to be complete, and will be killed off at the end of the tick.
        """
        return False

    def afterPhysics(self):
        """
        Called once every tick in the simulation, *after* physics has been applied.
        """
        pass

    def tearDown(self):
        """Called before the interactor is killed, so that it can do any cleanup necessary."""
        pass

    def handleEvent(self, event):
        """
        Override with code to be executed for every `pygame.event.EventType` (https://www.pygame.org/docs/ref/event.html).

        :param pygame.event.Event event: The pygame event registered.
        """
        pass

def fromOptions(options):
    if 'filename' in options:
        import yaml
        from ev3sim.file_helper import find_abs
        fname = find_abs(options['filename'])
        with open(fname, 'r') as f:
            config = yaml.safe_load(f)
            return fromOptions(config)
    if 'class_path' not in options:
        raise ValueError("Your options has no 'class_path' or 'filename' entry (Or the file you reference has no 'class_path' entry')")
    mname, cname = options['class_path'].rsplit('.', 1)
    import importlib
    klass = getattr(importlib.import_module(mname), cname)
    return klass(*options.get('args', []), **options.get('kwargs', {}))
