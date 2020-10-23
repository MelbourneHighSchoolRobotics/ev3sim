import multiprocessing
from os import getcwd
from queue import Empty, Queue as NonMultiQueue
import sys
from time import sleep
from unittest import mock
from ev3sim.constants import DEVICE_WRITE
from ev3dev2 import Device, DeviceNotFound

cur_events = NonMultiQueue()
tick = 0
tick_rate = 30
current_data = {}
last_checked_tick = -1

def attach_bot(robot_id, filename, result_queue, rq, sq):
    called_from = getcwd()

    try:
        sleep_builtin = sleep
        print_builtin = print
        def print_mock(*objects, sep=" ", end="\n"):
            message = sep.join(str(obj) for obj in objects) + end
            print_builtin(f"[{robot_id}] " + message, end="")

        @mock.patch("builtins.print", print_mock)
        def run_code(fname, recv_q: multiprocessing.Queue, send_q: multiprocessing.Queue):
            ### TIMING FUNCTIONS

            def wait_for_tick():
                global tick, tick_rate, current_data, cur_events
                recved = 0
                msg = {}
                while True:
                    try:
                        msg = recv_q.get_nowait()
                        recved += 1
                    except Empty:
                        # Once we've exhausted the queue, break and deal with the latest msg.
                        if recved > 0:
                            break
                        sleep_builtin(0.01)
                tick = msg["tick"]
                tick_rate = msg["tick_rate"]
                current_data = msg["data"]
                for ev in msg["events"]:
                    cur_events.put(ev)

            def get_time():
                return tick / tick_rate

            def sleep(seconds):
                cur = get_time()
                while True:
                    elapsed = get_time() - cur
                    if elapsed >= seconds:
                        return
                    wait_for_tick()

            ### CODE HELPERS

            @classmethod
            def handle_events(cls):
                """Since we can only handle events in mocked function calls, define a function to handle all of the existing events."""
                while cur_events.qsize():
                    event_name, event_data = cur_events.get()
                    func = getattr(cls, event_name)
                    func(event_data)
            
            fake_path = sys.path.copy()
            fake_path.append(called_from)

            ### EV3DEV2 MOCKS

            class MockedFile:
                def __init__(self, data_path):
                    self.k2, self.k3, self.k4 = data_path
                    self.seek_point = 0

                def read(self):
                    if isinstance(current_data[self.k2][self.k3][self.k4], int):
                        res = str(current_data[self.k2][self.k3][self.k4])
                    elif isinstance(current_data[self.k2][self.k3][self.k4], str):
                        if self.seek_point == 0:
                            res = current_data[self.k2][self.k3][self.k4]
                        else:
                            res = current_data[self.k2][self.k3][self.k4][self.seek_point :]
                    else:
                        raise ValueError(f"Not sure how to handle datatype {type(current_data[self.k2][self.k3][self.k4])}")
                    return res.encode("utf-8")

                def seek(self, i):
                    self.seek_point = i

                def write(self, value):
                    send_q.put((DEVICE_WRITE, (f"{self.k2} {self.k3} {self.k4}", value.decode())))

                def flush(self):
                    pass
            
            def device__init__(self, class_name, name_pattern="*", name_exact=False, **kwargs):
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
                    for name in current_data[self._path[0]].keys():
                        for k in kwargs:
                            if k not in current_data[self._path[0]][name]:
                                break
                            if isinstance(kwargs[k], list):
                                if current_data[self._path[0]][name][k] not in kwargs[k]:
                                    break
                            else:
                                if current_data[self._path[0]][name][k] != kwargs[k]:
                                    break
                        else:
                            self._path.append(name)
                            self._device_index = get_index(name)
                            break
                    else:
                        # Debug print for adding new devices.
                        # print(kwargs, data["current_data"][self._path[0]])
                        self._device_index = None

                        raise DeviceNotFound("%s is not connected." % self)

            def _attribute_file_open(self, name):
                return MockedFile((self._path[0], self._path[1], name))

            def wait(self, cond, timeout=None):
                tic = get_time()
                if cond(self.state):
                    return True
                # Register to active_data_handlers so we can do something every tick without lagging.
                while True:
                    wait_for_tick()
                    res = cond(self.state)
                    if res or ((timeout is not None) and (get_time() >= tic + timeout / 1000)):
                        return cond(self.state)
            
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

                    if self.on_change is not None and changed_names:
                        self.on_change([(name, name in new_state) for name in changed_names])

                    self.previous_presses = new_state

            orig_import = __import__

            def import_mock(name, *args):
                if name in ("fcntl", "evdev"):
                    return mock.Mock()
                return orig_import(name, *args)

            @mock.patch("time.time", get_time)
            @mock.patch("time.sleep", sleep)
            @mock.patch("ev3dev2.motor.Motor.wait", wait)
            @mock.patch("ev3dev2.Device.__init__", device__init__)
            @mock.patch("ev3dev2.Device._attribute_file_open", _attribute_file_open)
            @mock.patch("ev3dev2.button.Button", MockedButton)
            @mock.patch("ev3sim.code_helpers.is_ev3", False)
            @mock.patch("ev3sim.code_helpers.is_sim", True)
            @mock.patch("ev3sim.code_helpers.robot_id", robot_id)
            @mock.patch("ev3sim.code_helpers.wait_for_tick", wait_for_tick)
            @mock.patch("builtins.__import__", import_mock)
            @mock.patch("ev3sim.code_helpers.EventSystem.handle_events", handle_events)
            @mock.patch("sys.path", fake_path)
            def run_script(fname):
                from importlib.machinery import SourceFileLoader
                wait_for_tick()
                module = SourceFileLoader("__main__", fname).load_module()

            try:
                import ev3dev

                def raiseEV3Error():
                    raise ValueError(
                        "This simulator is not compatible with ev3dev. Please use ev3dev2: https://pypi.org/project/python-ev3dev2/"
                    )
                run_script = mock.patch("ev3dev.core.Device.__init__", raiseEV3Error)(run_script)
            except:
                pass
        
            run_script(fname)
        run_code(filename, rq, sq)
    except Exception as e:
        import traceback
        result_queue.put((robot_id, traceback.format_exc()))
        return
