# DEV_NOTE: If you want to change the data types in comm_schema.proto, then you need to regenerate the two pb2 files.
# To do this, run
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ev3sim/simulation/comm_schema.proto

from concurrent import futures
import logging

import grpc

import ev3sim.simulation.comm_schema_pb2
import ev3sim.simulation.comm_schema_pb2_grpc
import collections
import json
import threading
from queue import Queue
from ev3sim.simulation.loader import ScriptLoader

def start_server_with_shared_data(data, result):
    try:
        class SimulationDealer(ev3sim.simulation.comm_schema_pb2_grpc.SimulationDealerServicer):

            def RequestTickUpdates(self, request, context):
                rob_id = request.robot_id
                if rob_id not in data['active_count']:
                    data['active_count'][rob_id] = 0
                data['active_count'][rob_id] += 1
                data['bot_locks'][rob_id] = {
                    'lock': threading.Lock()
                }
                data['bot_locks'][rob_id]['condition_waiting'] = threading.Condition(data['bot_locks'][rob_id]['lock'])
                data['bot_locks'][rob_id]['condition_changing'] = threading.Condition(data['bot_locks'][rob_id]['lock'])
                c = data['active_count'][rob_id]
                data['data_queue'][rob_id] = Queue(maxsize=0)
                while True:
                    if data['active_count'][rob_id] != c:
                        return
                    # if no data is added for a second, then simulation has hung. Die.
                    try:
                        res = data['data_queue'][rob_id].get(timeout=1)
                    except:
                        return
                    tick = data['tick']
                    yield ev3sim.simulation.comm_schema_pb2.RobotData(tick=tick, tick_rate=ScriptLoader.instance.GAME_TICK_RATE, content=json.dumps(res))

            def SendWriteInfo(self, request, context):
                rob_id = request.robot_id
                attribute_path = request.attribute_path
                value = request.value
                data['write_stack'].append((rob_id, attribute_path, value))
                return ev3sim.simulation.comm_schema_pb2.WriteResult(result=True)

            def RequestServer(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                if key in data['bot_communications_data']:
                    return ev3sim.simulation.comm_schema_pb2.ServerResult(result=False, msg="Server already exists on this address")
                data['bot_communications_data'][key] = {
                    'server_id': rob_id,
                    'connections': {},
                    'client_queue': Queue(),
                }
                for locks in data['bot_locks'].values():
                    with locks['condition_changing']:
                        locks['condition_waiting'].notify()
                return ev3sim.simulation.comm_schema_pb2.ServerResult(result=True, msg="")

            def RequestConnect(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                with data['bot_locks'][rob_id]['condition_waiting']:
                    while True:
                        if key in data['bot_communications_data']:
                            if rob_id in data['bot_communications_data'][key]['connections']:
                                return ev3sim.simulation.comm_schema_pb2.ClientResult(result=False, host_robot_id='N/A', msg="This bot already has a connection to the server.")
                            data['bot_communications_data'][key]['connections'][rob_id] = {
                                'sends': Queue(0),
                                'recvs': Queue(0),
                            }
                            data['bot_communications_data'][key]['client_queue'].put(rob_id)
                            return ev3sim.simulation.comm_schema_pb2.ClientResult(result=True, host_robot_id=data['bot_communications_data'][key]['server_id'], msg="")
                        data['bot_locks'][rob_id]['condition_waiting'].wait(0.1)

            def RequestGetClient(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                if key not in data['bot_communications_data'] or data['bot_communications_data'][key]['server_id'] != rob_id:
                    return ev3sim.simulation.comm_schema_pb2.GetClientResult(result=False, client_id='N/A', msg="Server does not exist, or you are not the host of it.")    
                with data['bot_communications_data'][key]['client_queue'].not_empty:
                    while not data['bot_communications_data'][key]['client_queue']._qsize():
                        data['bot_communications_data'][key]['client_queue'].not_empty.wait(0.1)
                c_id = data['bot_communications_data'][key]['client_queue'].get(block=False)
                return ev3sim.simulation.comm_schema_pb2.GetClientResult(result=True, client_id=c_id, msg="")

            def RequestSend(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                client_id = request.client_id
                d = request.data
                if key not in data['bot_communications_data'] or (data['bot_communications_data'][key]['server_id'] not in (rob_id, client_id)):
                    return ev3sim.simulation.comm_schema_pb2.SendResult(result=False, msg="Server on address does not exist, or the incorrect Robot ID was specified.")
                if rob_id == data['bot_communications_data'][key]['server_id']:
                    data_keys = (client_id, 'recvs')
                else:
                    data_keys = (rob_id, 'sends')
                if data_keys[0] not in data['bot_communications_data'][key]['connections']:
                    return ev3sim.simulation.comm_schema_pb2.SendResult(result=False, msg="Server on address does not exist, or the incorrect Robot ID was specified.")
                data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]].put(d)
                # Wait for the request to be consumed.
                with data['bot_locks'][rob_id]['condition_waiting']:
                    while True:
                        if not data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]]._qsize():
                            return ev3sim.simulation.comm_schema_pb2.SendResult(result=True, msg="")
                        data['bot_locks'][rob_id]['condition_waiting'].wait(0.1)
            
            def RequestRecv(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                client_id = request.client_id
                if key not in data['bot_communications_data'] or (data['bot_communications_data'][key]['server_id'] not in (rob_id, client_id)):
                    return ev3sim.simulation.comm_schema_pb2.RecvResult(result=False, data='N/A', msg="Server on address does not exist, or the incorrect Sender ID was specified.")
                if rob_id == data['bot_communications_data'][key]['server_id']:
                    data_keys = (client_id, 'sends')
                else:
                    data_keys = (rob_id, 'recvs')
                if data_keys[0] not in data['bot_communications_data'][key]['connections']:
                    return ev3sim.simulation.comm_schema_pb2.RecvResult(result=False, data='N/A', msg="Server on address does not exist, or the incorrect Sender ID was specified.")
                with data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]].not_empty:
                    while not data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]]._qsize():
                        data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]].not_empty.wait(0.1)
                d = data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]].get()
                with data['bot_locks'][client_id]['condition_changing']:
                    data['bot_locks'][client_id]['condition_waiting'].notify()
                return ev3sim.simulation.comm_schema_pb2.RecvResult(data=d, result=True, msg="")


        def serve():
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            ev3sim.simulation.comm_schema_pb2_grpc.add_SimulationDealerServicer_to_server(SimulationDealer(), server)
            server.add_insecure_port('[::]:50051')
            server.start()
            server.wait_for_termination()

        logging.basicConfig()
        serve()
    except Exception as e:
        result.put(('Communications', e))