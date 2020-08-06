import sys
import logging
import grpc
import simulation.comm_schema_pb2
import simulation.comm_schema_pb2_grpc
import json
import time
from unittest import mock
from queue import Queue

robot_id = sys.argv[2]

def comms(data, result):
    logging.basicConfig()
    first_message = True
    with grpc.insecure_channel('localhost:50051') as channel:
        try:
            stub = simulation.comm_schema_pb2_grpc.SimulationDealerStub(channel)
            response = stub.RequestTickUpdates(simulation.comm_schema_pb2.RobotRequest(robot_id=robot_id))
            for r in response:
                data['tick'] = r.tick
                data['tick_rate'] = r.tick_rate
                data['current_data'] = json.loads(r.content)
                if first_message:
                    print("Connection initialised.")
                    print("-----------------------")
                    first_message = False
                    data['start_robot_queue'].put(True)
                for key in data['active_data_handlers']:
                    data['active_data_handlers'][key].put(True)
        except Exception as e:
            result.put(('Communications', e))

def write(data, result):
    with grpc.insecure_channel('localhost:50051') as channel:
        try:
            stub = simulation.comm_schema_pb2_grpc.SimulationDealerStub(channel)
            while True:
                path, value = data['actions_queue'].get()
                stub.SendWriteInfo(simulation.comm_schema_pb2.RobotWrite(robot_id=robot_id, attribute_path=path, value=value))
            response = stub.RequestTickUpdates(simulation.comm_schema_pb2.RobotRequest(robot_id=robot_id))
        except Exception as e:
            result.put(('Communications', e))

def robot(filename, data, result):
    try:
        from ev3dev2 import Device, DeviceNotFound

        class MockedFile:
            def __init__(self, data_path):
                self.k2, self.k3, self.k4 = data_path
                self.seek_point = 0
            
            def read(self):
                if isinstance(data['current_data'][self.k2][self.k3][self.k4], int):
                    res = str(data['current_data'][self.k2][self.k3][self.k4])
                if isinstance(data['current_data'][self.k2][self.k3][self.k4], str):
                    if self.seek_point == 0:
                        res = data['current_data'][self.k2][self.k3][self.k4]
                    else:
                        res = data['current_data'][self.k2][self.k3][self.k4][self.seek_point:]
                return res.encode('utf-8')
            
            def seek(self, i):
                self.seek_point = i
            
            def write(self, value):
                data['actions_queue'].put((f'{self.k2} {self.k3} {self.k4}', value.decode()))
                print(f"Wrote {self.k2} {self.k3} {self.k4} {value}")
            
            def flush(self):
                pass

        def device__init__(self, class_name, name_pattern='*', name_exact=False, **kwargs):
            print("Initialising device!")
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
                for name in data['current_data'][self._path[0]].keys():
                    for k in kwargs:
                        if k not in data['current_data'][self._path[0]][name]:
                            break
                        if isinstance(kwargs[k], list):
                            if data['current_data'][self._path[0]][name][k] not in kwargs[k]:
                                break
                        else:
                            if data['current_data'][self._path[0]][name][k] != kwargs[k]:
                                break
                    else:
                        self._path.append(name)
                        self._device_index = get_index(name)
                        break
                else:
                    print(kwargs, data['current_data'][self._path[0]])
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
            handler_key = ' ' .join(self._path)
            data['active_data_handlers'][handler_key] = Queue(maxsize=0)
            while True:
                data['active_data_handlers'][handler_key].get()
                res = cond(self.state)
                if res or ((timeout is not None) and (time.time() >= tic + timeout / 1000)):
                    del data['active_data_handlers'][handler_key]
                    return cond(self.state)

        def get_time():
            return data['tick'] / data['tick_rate']

        @mock.patch('time.time', mock.MagicMock(side_effect=get_time))
        @mock.patch('ev3dev2.motor.Motor.wait', wait)
        @mock.patch('ev3dev2.Device.__init__', device__init__)
        @mock.patch('ev3dev2.Device._attribute_file_open', _attribute_file_open)
        def run_script(fname):
            from importlib.machinery import SourceFileLoader
            module = SourceFileLoader('__main__', fname).load_module()
        
        assert data['start_robot_queue'].get(), "Something went wrong..."
        run_script(filename)
    except Exception as e:
        result.put(('Robots', e))
        return
    result.put(True)

shared_data = {
    'tick': 0,
    'tickrate': 1,
    'current_data': {},
    'actions_queue': Queue(maxsize=0),
    'start_robot_queue': Queue(maxsize=0),
    'active_data_handlers': {},
}

result_bucket = Queue(maxsize=1)

from threading import Thread

comm_thread = Thread(target=comms, args=(shared_data, result_bucket,), daemon=True)
robot_thread = Thread(target=robot, args=(sys.argv[1], shared_data, result_bucket,), daemon=True)
write_thread = Thread(target=write, args=(shared_data, result_bucket,), daemon=True)

comm_thread.start()
write_thread.start()
robot_thread.start()

try:
    with result_bucket.not_empty:
        while not result_bucket._qsize():
            result_bucket.not_empty.wait(1)
    r = result_bucket.get()
    if r is not True:
        print(f"An error occured in the {r[0]} thread. Raising an error now...")
        time.sleep(1)
        raise r[1]
    # This sleep is simply required for any final writes to be made on the communication thread.
    time.sleep(0.2)
except KeyboardInterrupt as e:
    raise KeyboardInterrupt()