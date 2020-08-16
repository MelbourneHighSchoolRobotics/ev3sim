# DEV_NOTE: If you want to change the data types in comm_schema.proto, then you need to regenerate the two pb2 files.
# To do this, run
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. simulation/comm_schema.proto
# ^ This is outdated ^

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
                data['bot_communications_data'][key] = {
                    'server_id': rob_id,
                    'connections': {},
                }
                for locks in data['bot_locks'].values():
                    with locks['condition_changing']:
                        locks['condition_waiting'].notify()
                return ev3sim.simulation.comm_schema_pb2.ServerResult()

            def RequestConnect(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                with data['bot_locks'][rob_id]['condition_waiting']:
                    while True:
                        if key in data['bot_communications_data']:
                            data['bot_communications_data'][key]['connections'][rob_id] = {
                                'sends': Queue(0),
                                'recvs': Queue(0),
                            }
                            return ev3sim.simulation.comm_schema_pb2.ClientResult(host_robot_id=data['bot_communications_data'][key]['server_id'])
                        data['bot_locks'][rob_id]['condition_waiting'].wait(0.1)

            def RequestSend(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                client_id = request.client_id
                d = request.data
                if rob_id == data['bot_communications_data'][key]['server_id']:
                    data_keys = (client_id, 'recvs')
                else:
                    data_keys = (rob_id, 'sends')
                data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]].push(d)
                # Wait for the request to be consumed.
                with data['bot_locks'][rob_id]['condition_waiting']:
                    if len(data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]]) == 0:
                        return ev3sim.simulation.comm_schema_pb2.SendResult()
                    data['bot_locks'][rob_id]['condition_waiting'].wait(0.1)
            
            def RequestRecv(self, request, context):
                rob_id = request.robot_id
                key = f'{request.address}:{request.port}'
                client_id = request.client_id
                if rob_id == data['bot_communications_data'][key]['server_id']:
                    data_keys = (client_id, 'sends')
                else:
                    data_keys = (rob_id, 'recvs')
                d = data['bot_communications_data'][key]['connections'][data_keys[0]][data_keys[1]].get()
                with data['bot_locks'][client_id]['condition_changing']:
                    data['bot_locks'][client_id]['condition_waiting'].notify()
                return ev3sim.simulation.comm_schema_pb2.RecvResult(data=d)


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