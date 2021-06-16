import os
from ev3sim.file_helper import find_abs_directory
from ev3sim.visual.manager import ScreenObjectManager


class Logger:

    LOG_CONSOLE = True

    instance: "Logger"

    def __init__(self):
        Logger.instance = self

    def getFilename(self, robot_id):
        from ev3sim.simulation.loader import StateHandler

        if StateHandler.WORKSPACE_FOLDER:
            log_dir = find_abs_directory("workspace/logs/", create=True)
        else:
            log_dir = find_abs_directory("package/logs/", create=True)
        return os.path.join(log_dir, f"{robot_id}_log.txt")

    def beginLog(self, robot_id):
        fname = self.getFilename(robot_id)
        if os.path.exists(fname):
            os.remove(fname)
        with open(fname, "w") as _:
            # Don't write anything
            pass

    def writeMessage(self, robot_id, msg, **kwargs):
        if Logger.LOG_CONSOLE:
            ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SIM].printStyledMessage(
                f"[{robot_id}] {msg}", **kwargs
            )
        # Remove formatting.
        msg = msg.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("</font>", "")
        split = msg.split("<font")
        for x in range(1, len(split) - 1):
            split[x] = ">".join(split[x].split(">")[1:])
        with open(self.getFilename(robot_id), "a") as f:
            f.write(msg)

    def reportError(self, robot_id, traceback):
        if Logger.LOG_CONSOLE:
            robot_index = int(robot_id.split("-")[1])
            ScreenObjectManager.instance.screens[ScreenObjectManager.SCREEN_SIM].printError(robot_index)
        with open(self.getFilename(robot_id), "a") as f:
            f.write(traceback)

    def openLog(self, robot_id):
        from ev3sim.utils import open_file, APP_EXPLORER

        open_file(self.getFilename(robot_id), APP_EXPLORER)
