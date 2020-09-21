import argparse
import sys
import threading
from collections import deque
from queue import Queue
import time
from ev3sim.file_helper import find_abs
import yaml
from unittest import mock
from ev3sim.simulation.loader import runFromConfig, ScriptLoader
from ev3sim.visual.manager import ScreenObjectManager
from os import getcwd
from ev3dev2 import Device, DeviceNotFound

shared_data = {
    "tick": 0,  # Current tick.
    "write_stack": deque(),  # All write actions are processed through this.
    "current_data": {},  # Simulation data for each bot.
    "active_count": {},  # Keeps track of which code connection each bot has.
    "bot_locks": {},  # Threading Locks and Conditions for each bot to wait for connection actions.
    "bot_communications_data": {},  # Buffers and information for all bot communications.
    "tick_updates": {},  # Simply a dictionary where the simulation tick will push static data, so the other methods are aware of when the simulation has exited.
    "events": {},  # Any events that should be sent to robots.
    "tick_locks": {},
    "last_checked_tick": {},
    "thread_ids": {},
    "write_blocking_ticks": {},
}
shared_data["tick_locks"]["main"] = {
    "lock": threading.Lock()
}
shared_data["tick_locks"]["main"]["cond"] = threading.Condition(shared_data["tick_locks"]["main"]["lock"])

print_builtin = print

def print_mock(*objects, sep=" ", end="\n", **kwargs):    
    message = sep.join(str(obj) for obj in objects) + end
    thread_id = threading.get_ident()
    if thread_id in shared_data["thread_ids"]:
        name = shared_data["thread_ids"][thread_id]
        print_builtin(f"[{name}] {message}", end="", **kwargs)
    else:
        print_builtin(*objects, sep=sep, end=end, **kwargs)

orig_import = __import__

def import_mock(name, *args):
    if name in ("fcntl", "evdev"):
        return mock.Mock()
    return orig_import(name, *args)

called_from = getcwd()
fake_path = sys.path.copy()
fake_path.append(called_from)

class MockedButton:
    class MockedButtonSpecific(Device):
        _pressed = None

        @property
        def pressed(self):
            self._pressed, value = self.get_attr_int(self._pressed, "pressed")
            return value

    button_names = ["up", "down", "left", "right", "enter", "backspace"]
    on_up = None
    on_down = None
    on_left = None
    on_right = None
    on_enter = None
    on_backspace = None
    on_change = None

    previous_presses = None

    def __init__(self):
        self.button_classes = {}
        for name in self.button_names:
            try:
                self.button_classes[name] = MockedButton.MockedButtonSpecific(
                    "brick_button", address=name
                )
            except Exception as e:
                if name == "up":
                    raise e
                self.button_classes[name] = None

    @property
    def buttons_pressed(self):
        pressed = []
        for name, obj in self.button_classes.items():
            if obj is not None and obj.pressed:
                pressed.append(name)
        return pressed

    @property
    def up(self):
        if self.button_classes["up"] is None:
            raise ValueError("Up button not connected.")
        return "up" in self.buttons_pressed

    @property
    def down(self):
        if self.button_classes["down"] is None:
            raise ValueError("Down button not connected.")
        return "down" in self.buttons_pressed

    @property
    def left(self):
        if self.button_classes["left"] is None:
            raise ValueError("Left button not connected.")
        return "left" in self.buttons_pressed

    @property
    def right(self):
        if self.button_classes["right"] is None:
            raise ValueError("Right button not connected.")
        return "right" in self.buttons_pressed

    @property
    def enter(self):
        if self.button_classes["enter"] is None:
            raise ValueError("Enter button not connected.")
        return "enter" in self.buttons_pressed

    @property
    def backspace(self):
        if self.button_classes["backspace"] is None:
            raise ValueError("Backspace button not connected.")
        return "backspace" in self.buttons_pressed

    def process(self, new_state=None):
        if new_state is None:
            new_state = set(self.buttons_pressed)
        if self.previous_presses is None:
            self.previous_presses = new_state

        changed_names = new_state.symmetric_difference(self.previous_presses)
        for name in changed_names:
            bound_method = getattr(self, f"on_{name}")

            if bound_method is not None:
                bound_method(name in new_state)

        if self.on_change is not None and state_diff:
            self.on_change([(name, name in new_state) for name in changed_names])

        self.previous_presses = new_state

@classmethod
def handle_events(cls):
    """Since we can only handle events in mocked function calls, define a function to handle all of the existing events."""
    robot_id = shared_data["thread_ids"][threading.get_ident()]
    while shared_data["events"][robot_id].qsize():
        event_name, event_data = shared_data["events"][robot_id].get()
        func = getattr(cls, event_name)
        func(event_data)

class MockedFile:
    def __init__(self, data_path):
        robot_id = shared_data["thread_ids"][threading.get_ident()]
        self.k2, self.k3, self.k4 = data_path
        if self.k4 == "mode":
            shared_data["write_blocking_ticks"][robot_id][f"{self.k2} {self.k3} {self.k4}"] = -1
        self.seek_point = 0

    def read(self):
        robot_id = shared_data["thread_ids"][threading.get_ident()]
        mode_string = f"{self.k2} {self.k3} mode"
        if mode_string in shared_data["write_blocking_ticks"][robot_id]:
            while shared_data["write_blocking_ticks"][robot_id][mode_string] >= shared_data["tick"]:
                shared_data["last_checked_tick"][robot_id] = shared_data["tick"]
                wait_for_tick()
        if isinstance(shared_data["current_data"][robot_id][self.k2][self.k3][self.k4], int):
            res = str(shared_data["current_data"][robot_id][self.k2][self.k3][self.k4])
        if isinstance(shared_data["current_data"][robot_id][self.k2][self.k3][self.k4], str):
            if self.seek_point == 0:
                res = shared_data["current_data"][robot_id][self.k2][self.k3][self.k4]
            else:
                res = shared_data["current_data"][robot_id][self.k2][self.k3][self.k4][self.seek_point :]
        return res.encode("utf-8")

    def seek(self, i):
        self.seek_point = i

    def write(self, value):
        robot_id = shared_data["thread_ids"][threading.get_ident()]
        shared_data["write_stack"].append((robot_id, f"{self.k2} {self.k3} {self.k4}", value.decode()))
        if self.k4 == "mode":
            shared_data["write_blocking_ticks"][robot_id][f"{self.k2} {self.k3} {self.k4}"] = shared_data["tick"]

    def flush(self):
        pass

def device__init__(self, class_name, name_pattern="*", name_exact=False, **kwargs):
    robot_id = shared_data["thread_ids"][threading.get_ident()]
    self._path = [class_name]
    self.kwargs = kwargs
    self._attr_cache = {}

    def get_index(file):
        match = Device._DEVICE_INDEX.match(file)
        if match:
            return int(match.group(1))
        else:
            return None

    if name_exact:
        self._path.append(name_pattern)
        self._device_index = get_index(name_pattern)
    else:
        for name in shared_data["current_data"][robot_id][self._path[0]].keys():
            for k in kwargs:
                if k not in shared_data["current_data"][robot_id][self._path[0]][name]:
                    break
                if isinstance(kwargs[k], list):
                    if shared_data["current_data"][robot_id][self._path[0]][name][k] not in kwargs[k]:
                        break
                else:
                    if shared_data["current_data"][robot_id][self._path[0]][name][k] != kwargs[k]:
                        break
            else:
                self._path.append(name)
                self._device_index = get_index(name)
                break
        else:
            # Debug print for adding new devices.
            # print(kwargs, shared_data["current_data"][robot_id][self._path[0]])
            self._device_index = None

            raise DeviceNotFound("%s is not connected." % self)

def _attribute_file_open(self, name):
    return MockedFile((self._path[0], self._path[1], name))

def wait(self, cond, timeout=None):
    robot_id = shared_data["thread_ids"][threading.get_ident()]
    import time

    tic = time.time()
    if cond(self.state):
        return True
    with shared_data["tick_locks"][robot_id]["cond"]:
        while True:
            shared_data["tick_locks"][robot_id]["cond"].wait()
            res = cond(self.state)
            if res or ((timeout is not None) and (time.time() >= tic + timeout / 1000)):
                return cond(self.state)

builtin_time = time.time

def get_time():
    thread_id = threading.get_ident()
    if thread_id in shared_data["thread_ids"] and shared_data["thread_ids"][thread_id] != "Simulator":
        return shared_data["tick"] / shared_data["tick_rate"]
    return builtin_time()

builtin_sleep = time.sleep

def sleep(seconds):
    robot_id = shared_data["thread_ids"][threading.get_ident()]
    thread_id = threading.get_ident()
    if thread_id in shared_data["thread_ids"] and shared_data["thread_ids"][thread_id] != "Simulator":
        from time import time

        cur = time()
        with shared_data["tick_locks"][robot_id]["cond"]:
            while True:
                elapsed = time() - cur
                if elapsed >= seconds:
                    return
                shared_data["tick_locks"][robot_id]["cond"].wait()
    return builtin_sleep(seconds)

def wait_for_tick():
    robot_id = shared_data["thread_ids"][threading.get_ident()]
    if shared_data["last_checked_tick"][robot_id] == shared_data["tick"]:
        with shared_data["tick_locks"][robot_id]["cond"]:
            shared_data["tick_locks"][robot_id]["cond"].wait()
            shared_data["last_checked_tick"][robot_id] = shared_data["tick"]

def raiseEV3Error(*args, **kwargs):
    raise ValueError(
        "This simulator is not compatible with ev3dev. Please use ev3dev2: https://pypi.org/project/python-ev3dev2/"
    )


@mock.patch("time.time", get_time)
@mock.patch("time.sleep", sleep)
@mock.patch("ev3dev2.motor.Motor.wait", wait)
@mock.patch("ev3dev2.Device.__init__", device__init__)
@mock.patch("ev3dev2.Device._attribute_file_open", _attribute_file_open)
@mock.patch("ev3dev2.button.Button", MockedButton)
@mock.patch("ev3sim.code_helpers.is_ev3", False)
@mock.patch("ev3sim.code_helpers.is_sim", True)
@mock.patch("ev3sim.code_helpers.wait_for_tick", wait_for_tick)
@mock.patch("builtins.__import__", import_mock)
@mock.patch("ev3sim.code_helpers.EventSystem.handle_events", handle_events)
@mock.patch("sys.path", fake_path)
@mock.patch("builtins.print", print_mock)
def single_run(preset_filename, robots, bind_addr, batch_file, bot_data):
    if batch_file:
        ScreenObjectManager.BATCH_FILE = batch_file
    ScreenObjectManager.PRESET_FILE = preset_filename
    preset_file = find_abs(preset_filename, allowed_areas=["local", "local/presets/", "package", "package/presets/"])
    with open(preset_file, "r") as f:
        config = yaml.safe_load(f)

    config["robots"] = config.get("robots", []) + robots


    def run(shared_data, result):
        shared_data["thread_ids"][threading.get_ident()] = "Simulator"
        shared_data["tick_rate"] = ScriptLoader.GAME_TICK_RATE
        try:
            runFromConfig(config, shared_data)
        except Exception as e:
            result.put(("Simulation", e))
            return
        result.put(True)
    
    # Handle any other settings modified by the preset.
    settings = config.get("settings", {})
    for keyword, value in settings.items():
        run = mock.patch(keyword, value)(run)

    result_bucket = Queue(maxsize=1)

    from threading import Thread
    from ev3sim.batch_attach import main as attach

    sim_thread = Thread(target=run, args=(shared_data, result_bucket), daemon=True)
    bot_threads = []
    for script, bot_id in bot_data:
        bot_threads.append(Thread(target=attach, args=(shared_data, script, bot_id), daemon=True))

    sim_thread.start()
    # Wait for a tick to occur.
    with shared_data["tick_locks"]["main"]["cond"]:
        shared_data["tick_locks"]["main"]["cond"].wait()
    for thread in bot_threads:
        thread.start()

    try:
        with result_bucket.not_empty:
            while not result_bucket._qsize():
                result_bucket.not_empty.wait(0.1)
        r = result_bucket.get()
        # Chuck it back on the queue so that other threads know we are quitting.
        result_bucket.put(r)
        if r is not True:
            print(f"An error occurred in the {r[0]} thread. Raising an error now...")
            time.sleep(1)
            raise r[1]
    except KeyboardInterrupt:
        pass

try:
    import ev3dev

    single_run = mock.patch("ev3dev.core.Device.__init__", raiseEV3Error)(single_run)
except:
    pass
