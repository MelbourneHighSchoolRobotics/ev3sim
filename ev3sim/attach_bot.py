import multiprocessing
import importlib
from os import getcwd
from queue import Empty, Queue as NonMultiQueue
import sys
from time import sleep
from unittest import mock
from ev3sim.constants import *
from ev3dev2 import Device, DeviceNotFound

cur_events = NonMultiQueue()
tick = 0
tick_rate = 30
current_data = {}
last_checked_tick = -1
communications_messages = NonMultiQueue()
input_messages = NonMultiQueue()


def safe_patch(mname, cname, obj):
    try:
        getattr(importlib.import_module(mname), cname.split(".", 1)[0])
    except Exception as e:
        return lambda f: f
    return mock.patch(f"{mname}.{cname}", obj)


def attach_bot(robot_id, filename, fake_roots, result_queue, result_queue_internal, rq, rq_internal, sq, sq_internal):
    result_queue._internal_size = result_queue_internal
    rq._internal_size = rq_internal
    sq._internal_size = sq_internal
    called_from = getcwd()

    try:
        sleep_builtin = sleep

        def print_mock(*objects, sep=" ", end="\n"):
            message = sep.join(str(obj) for obj in objects) + end
            sq.put(
                (
                    MESSAGE_PRINT,
                    {
                        "robot_id": robot_id,
                        "data": message,
                    },
                )
            )

        def format_print_mock(*objects, alive_id=None, life=3, sep=" ", end="\n"):
            message = sep.join(str(obj) for obj in objects) + end
            sq.put(
                (
                    MESSAGE_PRINT,
                    {
                        "robot_id": robot_id,
                        "data": message,
                        "kwargs": {
                            "alive_id": alive_id,
                            "life": life,
                        },
                    },
                )
            )

        @mock.patch("builtins.print", print_mock)
        @mock.patch("ev3sim.code_helpers.format_print", format_print_mock)
        def run_code(fname, fake_roots, recv_q: multiprocessing.Queue, send_q: multiprocessing.Queue):
            ### TIMING FUNCTIONS

            def handle_recv(msg_type, msg):
                global tick, tick_rate, current_data, cur_events
                if msg_type == SIM_DATA:
                    tick = msg["tick"]
                    tick_rate = msg["tick_rate"]
                    current_data = msg["data"]
                    if isinstance(current_data, str):
                        # Not pretty but it works.
                        e = Exception(current_data)
                        raise e
                    for ev in msg["events"]:
                        cur_events.put(ev)
                    return msg_type, msg
                elif msg_type == SIM_INPUT:
                    input_messages.put((msg_type, msg))
                else:
                    communications_messages.put((msg_type, msg))

            def wait_for_tick():
                recved = 0
                msg_type = -1
                msg = {}
                while True:
                    try:
                        msg_type, msg = recv_q.get_nowait()
                        handle_recv(msg_type, msg)
                        if msg_type != SIM_DATA:
                            break
                        recved += 1
                    except Empty:
                        # Once we've exhausted the queue, and all of our information has been used, break and deal with the latest msg.
                        if recved > 0 and send_q.qsize() == 0:
                            break
                        sleep_builtin(0.01)

            def get_time():
                return tick / tick_rate

            def sleep(seconds):
                cur = get_time()
                while True:
                    elapsed = get_time() - cur
                    if elapsed >= seconds:
                        return
                    wait_for_tick()

            def wait_for_msg_of_type(MSG_TYPE):
                while True:
                    try:
                        msg_type, msg = communications_messages.get_nowait()
                        if msg_type != MSG_TYPE:
                            communications_messages.put((msg_type, msg))
                            wait_for_tick()
                        else:
                            return msg
                    except Empty:
                        wait_for_tick()

            def fake_input(message=None):
                sq.put(
                    (
                        MESSAGE_INPUT_REQUESTED,
                        {
                            "robot_id": robot_id,
                            "message": str(message),
                        },
                    )
                )
                while True:
                    try:
                        _, msg = input_messages.get_nowait()
                        return msg
                    except Empty:
                        wait_for_tick()

            ### COMMUNICATIONS
            class MockedCommSocket:
                def __init__(self, hostaddr, port, sender_id):
                    self.hostaddr = hostaddr
                    self.port = str(port)
                    self.sender_id = sender_id

                def send(self, d):
                    assert isinstance(d, str), "Can only send string data through simulator."
                    send_q.put(
                        (
                            SEND_DATA,
                            {
                                "robot_id": robot_id,
                                "send_to": self.sender_id,
                                "connection_string": f"{self.hostaddr}:{self.port}",
                                "data": d,
                            },
                        )
                    )
                    wait_for_msg_of_type(SEND_SUCCESS)

                def recv(self, buffer):
                    # At the moment the buffer is ignored.
                    msg = wait_for_msg_of_type(RECV_DATA)
                    return msg["data"]

                def close(self):
                    send_q.put(
                        (
                            CLOSE_CLIENT,
                            {
                                "robot_id": robot_id,
                                "connection_string": f"{self.hostaddr}:{self.port}",
                            },
                        )
                    )
                    msg = wait_for_msg_of_type(CLIENT_CLOSED)

            class MockedCommClient(MockedCommSocket):
                def __init__(self, hostaddr, port):
                    if hostaddr == "aa:bb:cc:dd:ee:ff":
                        print(
                            f"While this example will work, for competition bots please change the host address from {hostaddr} so competing bots can communicate separately."
                        )
                    send_q.put(
                        (
                            JOIN_CLIENT,
                            {
                                "robot_id": robot_id,
                                "connection_string": f"{hostaddr}:{port}",
                            },
                        )
                    )
                    msg = wait_for_msg_of_type(SUCCESS_CLIENT_CONNECTION)
                    sender_id = msg["host_id"]
                    print(f"Client connected to {sender_id}")
                    super().__init__(hostaddr, port, sender_id)

                def close(self):
                    super().close()

            class MockedCommServer:
                def __init__(self, hostaddr, port):
                    if hostaddr == "aa:bb:cc:dd:ee:ff":
                        print(
                            f"While this example will work, for competition bots please change the host address from {hostaddr} so competing bots can communicate separately."
                        )
                    self.hostaddr = hostaddr
                    self.port = str(port)
                    send_q.put(
                        (
                            START_SERVER,
                            {
                                "connection_string": f"{self.hostaddr}:{self.port}",
                                "robot_id": robot_id,
                            },
                        )
                    )
                    wait_for_msg_of_type(SERVER_SUCCESS)
                    print(f"Server started on {self.hostaddr}:{self.port}")
                    self.sockets = []

                def accept_client(self):
                    msg = wait_for_msg_of_type(NEW_CLIENT_CONNECTION)
                    self.sockets.append(MockedCommSocket(self.hostaddr, self.port, msg["client_id"]))
                    return self.sockets[-1], (self.hostaddr, self.port)

                def close(self):
                    # Close all clients, then close myself
                    for socket in self.sockets:
                        socket.close()
                    send_q.put(
                        (
                            CLOSE_SERVER,
                            {
                                "robot_id": robot_id,
                                "connection_string": f"{self.hostaddr}:{self.port}",
                            },
                        )
                    )
                    msg = wait_for_msg_of_type(SERVER_CLOSED)

            ### CODE HELPERS

            from ev3sim.code_helpers import CommandSystem

            class MockCommandSystem(CommandSystem):
                @classmethod
                def send_command(cls, command_type, command_data):
                    send_q.put(
                        (
                            BOT_COMMAND,
                            {
                                "robot_id": robot_id,
                                "command_type": command_type,
                                "payload": command_data,
                            },
                        )
                    )

            @classmethod
            def handle_events(cls):
                """Since we can only handle events in mocked function calls, define a function to handle all of the existing events."""
                while cur_events.qsize():
                    event_name, event_data = cur_events.get()
                    if hasattr(cls, event_name):
                        func = getattr(cls, event_name)
                        func(event_data)

            fake_path = sys.path.copy()
            fake_path.append(called_from)
            fake_path = fake_roots + fake_path

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
                        raise ValueError(
                            f"Not sure how to handle datatype {type(current_data[self.k2][self.k3][self.k4])}"
                        )
                    return res.encode("utf-8")

                def seek(self, i):
                    self.seek_point = i

                def write(self, value):
                    send_q.put((DEVICE_WRITE, (f"{self.k2} {self.k3} {self.k4}", value.decode())))
                    while self.k4 == "mode" and current_data[self.k2][self.k3][self.k4] != value.decode():
                        wait_for_tick()

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
                            self.button_classes[name] = MockedButton.MockedButtonSpecific("brick_button", address=name)
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

            def raiseEV3Error():
                raise ValueError(
                    "This simulator is not compatible with ev3dev. Please use ev3dev2: https://pypi.org/project/python-ev3dev2/"
                )

            @safe_patch("time", "time", get_time)
            @safe_patch("time", "sleep", sleep)
            @safe_patch("ev3dev2.motor", "Motor.wait", wait)
            @safe_patch("ev3dev2", "Device.__init__", device__init__)
            @safe_patch("ev3dev2", "Device._attribute_file_open", _attribute_file_open)
            @safe_patch("ev3dev2.button", "Button", MockedButton)
            @safe_patch("ev3sim.code_helpers", "is_ev3", False)
            @safe_patch("ev3sim.code_helpers", "is_sim", True)
            @safe_patch("ev3sim.code_helpers", "robot_id", robot_id)
            @safe_patch("ev3sim.code_helpers", "wait_for_tick", wait_for_tick)
            @safe_patch("ev3sim.code_helpers", "CommServer", MockedCommServer)
            @safe_patch("ev3sim.code_helpers", "CommClient", MockedCommClient)
            @safe_patch("ev3sim.code_helpers", "wait_for_tick", wait_for_tick)
            @safe_patch("builtins", "__import__", import_mock)
            @safe_patch("ev3sim.code_helpers", "CommandSystem", MockCommandSystem)
            @safe_patch("ev3sim.code_helpers", "EventSystem.handle_events", handle_events)
            @safe_patch("sys", "path", fake_path)
            @safe_patch("builtins", "input", fake_input)
            # These ev3dev2 objects are not implemented in the sim.
            @safe_patch("ev3dev2", "led", mock.Mock())
            @safe_patch("ev3dev2.led", "Leds", mock.Mock())
            @safe_patch("ev3dev2", "sound", mock.Mock())
            @safe_patch("ev3dev2.sound", "Sound", mock.Mock())
            @safe_patch("ev3dev2", "display", mock.Mock())
            @safe_patch("ev3dev2.display", "Display", mock.Mock())
            @safe_patch("ev3dev2", "console", mock.Mock())
            @safe_patch("ev3dev2.console", "Console", mock.Mock())
            # TODO: This should probably actually give reasonable values for voltage/current/amps
            @safe_patch("ev3dev2", "power", mock.Mock())
            @safe_patch("ev3dev2.power", "Power", mock.Mock())
            @safe_patch("ev3dev2", "fonts", mock.Mock())
            @safe_patch("ev3dev.core", "Device.__init__", raiseEV3Error)
            def run_script(fname):
                from importlib.machinery import SourceFileLoader

                wait_for_tick()
                module = SourceFileLoader("__main__", fname).load_module()

            run_script(fname)

        run_code(filename, fake_roots, rq, sq)
    except Exception as e:
        import traceback

        result_queue.put((robot_id, traceback.format_exc()))
        return
