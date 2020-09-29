import sys
import logging
import json
import time
import argparse
import grpc
import threading
import ev3sim.simulation.comm_schema_pb2
import ev3sim.simulation.comm_schema_pb2_grpc
from unittest import mock
from queue import Queue
from os import path, getcwd


def main(passed_args=None):
    called_from = getcwd()
    if passed_args is None:
        passed_args = sys.argv

    parser = argparse.ArgumentParser(description="Attach a valid ev3dev2 script to the simulation.")
    parser.add_argument("filename", type=str, help="The relative or absolute path of the script you want to run")
    parser.add_argument(
        "robot_id",
        nargs="?",
        type=str,
        help="The ID of the robot you wish to attach to. Right click a robot to copy it's ID to the clipboard. Defaults to the first robot spawned if unspecified.",
        default="Robot-0",
    )
    parser.add_argument(
        "--simulator_addr",
        default="localhost:50051",
        metavar="address:port",
        help="The IP address and port that the simulator is running on (you shouldn't need to change this). Default is localhost:50051.",
    )
    parser.add_argument("--send_logs", action="store_true", help="Send logs/`print` output to the simulator process")

    args = parser.parse_args(passed_args[1:])

    robot_id = args.robot_id

    shared_data = {
        "tick": 0,
        "tickrate": 1,
        "current_data": {},
        "actions_queue": Queue(maxsize=0),
        "start_robot_queue": Queue(maxsize=0),
        "active_data_handlers": {},
        "update_lock": threading.Lock(),
        "write_results": Queue(maxsize=0),
        "active_connections": [],
        "thread_ids": {},
        "events": Queue(maxsize=0),
        "write_blocking_ticks": {},
    }
    shared_data["condition_updated"] = threading.Condition(shared_data["update_lock"])
    shared_data["condition_updating"] = threading.Condition(shared_data["update_lock"])

    print_builtin = print

    def print_mock(*objects, sep=" ", end="\n", **kwargs):
        message = sep.join(str(obj) for obj in objects) + end
        thread_id = threading.get_ident()
        if thread_id in shared_data["thread_ids"]:
            source = shared_data["thread_ids"][thread_id]
            shared_data["actions_queue"].put(("send_log", (message, source)))
            if not args.send_logs:
                print_builtin(message, end="", **kwargs)
        else:
            print_builtin(*objects, sep=sep, end=end, **kwargs)

    @mock.patch("builtins.print", print_mock)
    def run_simulation():
        class CommunicationsError(Exception):
            pass

        def comms(data, result):
            data["thread_ids"][threading.get_ident()] = ev3sim.simulation.comm_schema_pb2.RobotLogSource.COMMS
            from grpc._channel import _MultiThreadedRendezvous

            logging.basicConfig()
            first_message = True
            while True:
                with grpc.insecure_channel(args.simulator_addr) as channel:
                    try:
                        stub = ev3sim.simulation.comm_schema_pb2_grpc.SimulationDealerStub(channel)
                        response = stub.RequestTickUpdates(
                            ev3sim.simulation.comm_schema_pb2.RobotRequest(robot_id=robot_id)
                        )
                        for r in response:
                            data["tick"] = r.tick
                            data["tick_rate"] = r.tick_rate
                            data["current_data"] = json.loads(r.content)
                            for e in data["current_data"]["events"]:
                                data["events"].put(e)
                            if first_message:
                                print("Connection initialised.")
                                first_message = False
                                data["start_robot_queue"].put(True)
                            for key in data["active_data_handlers"]:
                                data["active_data_handlers"][key].put(True)
                            with data["condition_updating"]:
                                data["condition_updated"].notify()
                    except Exception as e:
                        # https://github.com/MelbourneHighSchoolRobotics/ev3sim/issues/55 pygame window dragging will deadline.
                        if not (isinstance(e, _MultiThreadedRendezvous) and e._state.details == "Deadline Exceeded"):
                            result.put(("Communications", e))
                            break
                        # For some reason this needs to be done despite using the context manager.
                        channel.close()

        def write(data, result):
            data["thread_ids"][threading.get_ident()] = ev3sim.simulation.comm_schema_pb2.RobotLogSource.WRITE
            with grpc.insecure_channel(args.simulator_addr) as channel:
                try:
                    stub = ev3sim.simulation.comm_schema_pb2_grpc.SimulationDealerStub(channel)
                    while True:
                        action_type, info = data["actions_queue"].get()
                        if action_type == "write":
                            path, value = info
                            d = stub.SendWriteInfo(
                                ev3sim.simulation.comm_schema_pb2.RobotWrite(
                                    robot_id=robot_id, attribute_path=path, value=value
                                )
                            )
                            if path.split()[-1] == "mode":
                                data["write_results"].put(d)
                        elif action_type == "send_log":
                            message, source = info
                            stub.SendRobotLog(
                                ev3sim.simulation.comm_schema_pb2.RobotLogRequest(
                                    robot_id=robot_id, log=message, source=source, print=args.send_logs
                                )
                            )
                        elif action_type == "begin_server":
                            d = stub.RequestServer(ev3sim.simulation.comm_schema_pb2.ServerRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                        elif action_type == "connect":
                            d = stub.RequestConnect(ev3sim.simulation.comm_schema_pb2.ClientRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                        elif action_type == "accept_client":
                            d = stub.RequestGetClient(ev3sim.simulation.comm_schema_pb2.GetClientRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                        elif action_type == "send_data":
                            d = stub.RequestSend(ev3sim.simulation.comm_schema_pb2.SendRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                        elif action_type == "recv_data":
                            d = stub.RequestRecv(ev3sim.simulation.comm_schema_pb2.RecvRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                        elif action_type == "close_server":
                            d = stub.CloseServerConnection(ev3sim.simulation.comm_schema_pb2.CloseServerRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                        elif action_type == "close_client":
                            d = stub.CloseClientConnection(ev3sim.simulation.comm_schema_pb2.CloseClientRequest(**info))
                            if not d.result:
                                raise CommunicationsError(d.msg)
                            data["write_results"].put(d)
                except Exception as e:
                    result.put(("Communications", e))

        def robot(filename, data, result):
            data["thread_ids"][threading.get_ident()] = ev3sim.simulation.comm_schema_pb2.RobotLogSource.ROBOT
            try:
                from ev3dev2 import Device, DeviceNotFound

                @classmethod
                def handle_events(cls):
                    """Since we can only handle events in mocked function calls, define a function to handle all of the existing events."""
                    while data["events"].qsize():
                        event_name, event_data = data["events"].get()
                        func = getattr(cls, event_name)
                        func(event_data)

                class MockedFile:
                    def __init__(self, data_path):
                        self.k2, self.k3, self.k4 = data_path
                        if self.k4 == "mode":
                            data["write_blocking_ticks"][f"{self.k2} {self.k3} {self.k4}"] = -1
                        self.seek_point = 0

                    def read(self):
                        # If mode requires us to wait for values to update, then wait.
                        mode_string = f"{self.k2} {self.k3} mode"
                        if mode_string in data["write_blocking_ticks"]:
                            while data["write_blocking_ticks"][mode_string] >= data["tick"]:
                                data["last_checked_tick"] = data["tick"]
                                wait_for_tick()
                        if isinstance(data["current_data"][self.k2][self.k3][self.k4], int):
                            res = str(data["current_data"][self.k2][self.k3][self.k4])
                        if isinstance(data["current_data"][self.k2][self.k3][self.k4], str):
                            if self.seek_point == 0:
                                res = data["current_data"][self.k2][self.k3][self.k4]
                            else:
                                res = data["current_data"][self.k2][self.k3][self.k4][self.seek_point :]
                        return res.encode("utf-8")

                    def seek(self, i):
                        self.seek_point = i

                    def write(self, value):
                        data["actions_queue"].put(("write", (f"{self.k2} {self.k3} {self.k4}", value.decode())))
                        if self.k4 == "mode":
                            with data["write_results"].not_empty:
                                while not data["write_results"]._qsize():
                                    data["write_results"].not_empty.wait(0.1)
                            res = data["write_results"].get()
                            data["write_blocking_ticks"][f"{self.k2} {self.k3} {self.k4}"] = data["tick"]

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
                        for name in data["current_data"][self._path[0]].keys():
                            for k in kwargs:
                                if k not in data["current_data"][self._path[0]][name]:
                                    break
                                if isinstance(kwargs[k], list):
                                    if data["current_data"][self._path[0]][name][k] not in kwargs[k]:
                                        break
                                else:
                                    if data["current_data"][self._path[0]][name][k] != kwargs[k]:
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
                    import time

                    tic = time.time()
                    if cond(self.state):
                        return True
                    # Register to active_data_handlers so we can do something every tick without lagging.
                    handler_key = " ".join(self._path)
                    data["active_data_handlers"][handler_key] = Queue(maxsize=0)
                    while True:
                        data["active_data_handlers"][handler_key].get()
                        res = cond(self.state)
                        if res or ((timeout is not None) and (time.time() >= tic + timeout / 1000)):
                            del data["active_data_handlers"][handler_key]
                            return cond(self.state)

                def get_time():
                    return data["tick"] / data["tick_rate"]

                def sleep(seconds):
                    from time import time

                    cur = time()
                    with data["condition_updated"]:
                        while True:
                            elapsed = time() - cur
                            if elapsed >= seconds:
                                return
                            data["condition_updated"].wait(0.1)

                data["last_checked_tick"] = data["tick"]

                def wait_for_tick():
                    with data["condition_updated"]:
                        while data["actions_queue"].qsize():
                            data["condition_updated"].wait(0.1)
                        if data["last_checked_tick"] == data["tick"]:
                            while True:
                                if data["last_checked_tick"] != data["tick"]:
                                    data["last_checked_tick"] = data["tick"]
                                    return
                                data["condition_updated"].wait(0.1)

                def raiseEV3Error(*args, **kwargs):
                    raise ValueError(
                        "This simulator is not compatible with ev3dev. Please use ev3dev2: https://pypi.org/project/python-ev3dev2/"
                    )

                class MockedCommSocket:
                    def __init__(self, hostaddr, port, sender_id):
                        self.hostaddr = hostaddr
                        self.port = str(port)
                        self.sender_id = sender_id

                    def send(self, d):
                        assert isinstance(d, str), "Can only send string data through simulator."
                        data["actions_queue"].put(
                            (
                                "send_data",
                                {
                                    "robot_id": robot_id,
                                    "client_id": self.sender_id,
                                    "address": self.hostaddr,
                                    "port": self.port,
                                    "data": d,
                                },
                            )
                        )
                        # Wait for it to be handled
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        r = data["write_results"].get()

                    def recv(self, buffer):
                        # At the moment the buffer is ignored.
                        data["actions_queue"].put(
                            (
                                "recv_data",
                                {
                                    "robot_id": robot_id,
                                    "client_id": self.sender_id,
                                    "address": self.hostaddr,
                                    "port": self.port,
                                },
                            )
                        )
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        return data["write_results"].get().data

                    def close(self):
                        data["actions_queue"].put(
                            (
                                "close_client",
                                {
                                    "robot_id": robot_id,
                                    "address": self.hostaddr,
                                    "port": self.port,
                                    "server_id": self.sender_id,
                                },
                            )
                        )
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        info = data["write_results"].get()

                class MockedCommClient(MockedCommSocket):
                    def __init__(self, hostaddr, port):
                        if hostaddr == "aa:bb:cc:dd:ee:ff":
                            print(
                                f"While this example will work, for competition bots please change the host address from {hostaddr} so competing bots can communicate separately."
                            )
                        data["actions_queue"].put(
                            (
                                "connect",
                                {
                                    "robot_id": robot_id,
                                    "address": hostaddr,
                                    "port": str(port),
                                },
                            )
                        )
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        sender_id = data["write_results"].get().host_robot_id
                        super().__init__(hostaddr, port, sender_id)
                        data["active_connections"].append(self)

                    def close(self):
                        super().close()
                        data["active_connections"].remove(self)

                class MockedCommServer:
                    def __init__(self, hostaddr, port):
                        if hostaddr == "aa:bb:cc:dd:ee:ff":
                            print(
                                f"While this example will work, for competition bots please change the host address from {hostaddr} so competing bots can communicate separately."
                            )
                        self.hostaddr = hostaddr
                        self.port = str(port)
                        data["actions_queue"].put(
                            (
                                "begin_server",
                                {
                                    "robot_id": robot_id,
                                    "address": self.hostaddr,
                                    "port": self.port,
                                },
                            )
                        )
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        result = data["write_results"].get()
                        self.sockets = []
                        data["active_connections"].append(self)

                    def accept_client(self):
                        data["actions_queue"].put(
                            (
                                "accept_client",
                                {
                                    "robot_id": robot_id,
                                    "address": self.hostaddr,
                                    "port": self.port,
                                },
                            )
                        )
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        client = data["write_results"].get()
                        self.sockets.append(MockedCommSocket(self.hostaddr, self.port, client.client_id))
                        return self.sockets[-1], (self.hostaddr, self.port)

                    def close(self):
                        # Close all clients, then close myself
                        for socket in self.sockets:
                            socket.close()
                        data["actions_queue"].put(
                            (
                                "close_server",
                                {
                                    "robot_id": robot_id,
                                    "address": self.hostaddr,
                                    "port": self.port,
                                },
                            )
                        )
                        with data["write_results"].not_empty:
                            while not data["write_results"]._qsize():
                                data["write_results"].not_empty.wait(0.1)
                        info = data["write_results"].get()
                        data["active_connections"].remove(self)

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

                fake_path = sys.path.copy()
                fake_path.append(called_from)

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
                @mock.patch("ev3sim.code_helpers.CommServer", MockedCommServer)
                @mock.patch("ev3sim.code_helpers.CommClient", MockedCommClient)
                @mock.patch("ev3sim.code_helpers.wait_for_tick", wait_for_tick)
                @mock.patch("builtins.__import__", import_mock)
                @mock.patch("ev3sim.code_helpers.EventSystem.handle_events", handle_events)
                @mock.patch("sys.path", fake_path)
                def run_script(fname):
                    from importlib.machinery import SourceFileLoader

                    module = SourceFileLoader("__main__", fname).load_module()

                try:
                    import ev3dev

                    run_script = mock.patch("ev3dev.core.Device.__init__", raiseEV3Error)(run_script)
                except:
                    pass

                assert data["start_robot_queue"].get(), "Something went wrong..."
                run_script(filename)
            except Exception as e:
                result.put(("Robots", e))
                return
            result.put(True)

        result_bucket = Queue(maxsize=1)

        from threading import Thread
        from ev3sim.file_helper import find_abs

        comm_thread = Thread(
            target=comms,
            args=(
                shared_data,
                result_bucket,
            ),
            daemon=True,
        )
        robot_thread = Thread(
            target=robot,
            args=(
                find_abs(args.filename, allowed_areas=["local", "local/robots/", "package", "package/robots/"]),
                shared_data,
                result_bucket,
            ),
            daemon=True,
        )
        write_thread = Thread(
            target=write,
            args=(
                shared_data,
                result_bucket,
            ),
            daemon=True,
        )

        comm_thread.start()
        write_thread.start()
        robot_thread.start()

        try:
            with result_bucket.not_empty:
                while not result_bucket._qsize():
                    result_bucket.not_empty.wait(0.1)
            r = result_bucket.get()
            if r is not True:
                # Clear the actions queue.
                shared_data["actions_queue"] = Queue()
        except KeyboardInterrupt as e:
            r = True
            pass

        # Ensure all active connections are closed, provided the Communications thread is still running.
        if r is True or r[0] != "Communications":
            for active_connection in shared_data["active_connections"]:
                active_connection.close()

        with shared_data["condition_updated"]:
            while shared_data["actions_queue"]._qsize() > 0:
                shared_data["condition_updated"].wait(0.1)

            shared_data["condition_updated"].wait(0.5)

        if r is not True:
            print(f"An error occurred in the {r[0]} thread. Raising an error now...")
            raise r[1]

    run_simulation()


if __name__ == "__main__":
    main()
