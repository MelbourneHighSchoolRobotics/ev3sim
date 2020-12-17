class SimulatorMenu:
    def update(self, draw_time):
        pass

    def initWithKwargs(self, **kwargs):
        batch = kwargs.get("batch")
        from ev3sim.simulation.loader import StateHandler
        from ev3sim.simulation.world import World

        World.instance.resetWorld()

        StateHandler.instance.beginSimulation(batch=batch)

    def onPop(self):
        from ev3sim.simulation.loader import StateHandler, ScriptLoader

        # We need to close all previous communications with the bots.
        StateHandler.instance.closeProcesses()
        StateHandler.instance.is_simulating = False
        # We also need to reset the objects registered to the Screen.
        from ev3sim.visual.manager import ScreenObjectManager

        ScreenObjectManager.instance.resetVisualElements()
        # We also need to reset the physics sim.
        from ev3sim.simulation.world import World

        World.instance.resetWorld()
        # And reset the script loader.
        ScriptLoader.instance.reset()

    def process_events(self, event):
        pass

    def handleEvent(self, event):
        pass
