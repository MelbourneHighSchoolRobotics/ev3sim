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
import time
from queue import Queue
from ev3sim.simulation.loader import ScriptLoader

TICK_WAITING_TIMEOUT = 0.03
SIM_DIED_TIME = 0.3


def start_server_with_shared_data(data, result, bind_addr):
    try:

        print_lock = threading.Lock()

        class SimulationDealer(ev3sim.simulation.comm_schema_pb2_grpc.SimulationDealerServicer):
            def RequestTickUpdates(self, request, context):
                rob_id = request.robot_id
                if rob_id not in data["active_count"]:
                    data["active_count"][rob_id] = 0
                    data["bot_locks"][rob_id] = {"lock": threading.Lock()}
                data["active_count"][rob_id] += 1
                data["bot_locks"][rob_id]["condition_waiting"] = threading.Condition(data["bot_locks"][rob_id]["lock"])
                data["bot_locks"][rob_id]["condition_changing"] = threading.Condition(data["bot_locks"][rob_id]["lock"])
                c = data["active_count"][rob_id]
                data["data_queue"][rob_id] = Queue(maxsize=0)
                while True:
                    if data["active_count"][rob_id] != c:
                        return
                    # if no data is added for a second, then simulation has hung. Die.
                    try:
                        res = data["data_queue"][rob_id].get(timeout=SIM_DIED_TIME)
                    except:
                        return
                    tick = data["tick"]
                    # If there are any events, then pop them off and add to the payload.
                    res["events"] = []
                    while data["events"][rob_id].qsize():
                        res["events"].append(data["events"][rob_id].get())
                    yield ev3sim.simulation.comm_schema_pb2.RobotData(
                        tick=tick, tick_rate=ScriptLoader.instance.GAME_TICK_RATE, content=json.dumps(res)
                    )

            def SendWriteInfo(self, request, context):
                rob_id = request.robot_id
                attribute_path = request.attribute_path
                value = request.value
                data["write_stack"].append((rob_id, attribute_path, value))
                return ev3sim.simulation.comm_schema_pb2.WriteResult(result=True)

            def SendRobotLog(self, request, context):
                if request.print:
                    tag = f"[{request.robot_id}] "
                    lines = request.log.split("\n")
                    message = []
                    for i, line in enumerate(lines):
                        message.append(f"{tag}{line}" if line and i != len(lines) - 1 else line)
                    with print_lock:
                        print(*message, sep="\n", end="", flush=True)
                return ev3sim.simulation.comm_schema_pb2.RobotLogResult(result=True)

            def RequestServer(self, request, context):
                rob_id = request.robot_id
                if request.address == "aa:bb:cc:dd:ee:ff":
                    print(
                        f"While this example will work, for competition bots please change the host address from {request.address} so competing bots can communicate separately."
                    )
                key = f"{request.address}:{request.port}"
                if key in data["bot_communications_data"]:
                    return ev3sim.simulation.comm_schema_pb2.ServerResult(
                        result=False, msg="Server already exists on this address"
                    )
                data["bot_communications_data"][key] = {
                    "server_id": rob_id,
                    "connections": {},
                    "client_queue": Queue(),
                }
                for locks in data["bot_locks"].values():
                    with locks["condition_changing"]:
                        locks["condition_waiting"].notify()
                return ev3sim.simulation.comm_schema_pb2.ServerResult(result=True, msg="")

            def RequestConnect(self, request, context):
                rob_id = request.robot_id
                key = f"{request.address}:{request.port}"
                last_tick = time.time()
                update_key = f"{rob_id}:RC"
                data["tick_updates"][update_key] = Queue(0)
                try:
                    with data["bot_locks"][rob_id]["condition_waiting"]:
                        while True:
                            if key in data["bot_communications_data"]:
                                if (
                                    rob_id in data["bot_communications_data"][key]["connections"]
                                    or data["bot_communications_data"][key]["server_id"] == rob_id
                                ):
                                    return ev3sim.simulation.comm_schema_pb2.ClientResult(
                                        result=False,
                                        host_robot_id="N/A",
                                        msg="This bot already has a connection to the server.",
                                    )
                                data["bot_communications_data"][key]["connections"][rob_id] = {
                                    "sends": Queue(0),
                                    "recvs": Queue(0),
                                }
                                data["bot_communications_data"][key]["client_queue"].put(rob_id)
                                del data["tick_updates"][update_key]
                                return ev3sim.simulation.comm_schema_pb2.ClientResult(
                                    result=True, host_robot_id=data["bot_communications_data"][key]["server_id"], msg=""
                                )
                            data["bot_locks"][rob_id]["condition_waiting"].wait(TICK_WAITING_TIMEOUT)
                            try:
                                data["tick_updates"][update_key].get(timeout=TICK_WAITING_TIMEOUT)
                                last_tick = time.time()
                            except:
                                if result._qsize():
                                    return ev3sim.simulation.comm_schema_pb2.ClientResult(
                                        result=False, host_robot_id="N/A", msg="Simulation died."
                                    )
                except KeyError:
                    if update_key in data["tick_updates"]:
                        del data["tick_updates"][update_key]
                    return ev3sim.simulation.comm_schema_pb2.ClientResult(
                        result=False, host_robot_id="N/A", msg="Your connection was closed."
                    )

            def RequestGetClient(self, request, context):
                rob_id = request.robot_id
                key = f"{request.address}:{request.port}"
                if (
                    key not in data["bot_communications_data"]
                    or data["bot_communications_data"][key]["server_id"] != rob_id
                ):
                    return ev3sim.simulation.comm_schema_pb2.GetClientResult(
                        result=False, client_id="N/A", msg="Server does not exist, or you are not the host of it."
                    )
                last_tick = time.time()
                update_key = f"{rob_id}:RGC"
                data["tick_updates"][update_key] = Queue(0)
                try:
                    with data["bot_communications_data"][key]["client_queue"].not_empty:
                        while not data["bot_communications_data"][key]["client_queue"]._qsize():
                            data["bot_communications_data"][key]["client_queue"].not_empty.wait(TICK_WAITING_TIMEOUT)
                            try:
                                data["tick_updates"][update_key].get(timeout=TICK_WAITING_TIMEOUT)
                                last_tick = time.time()
                            except:
                                if result._qsize():
                                    return ev3sim.simulation.comm_schema_pb2.GetClientResult(
                                        result=False, client_id="N/A", msg="Simulation died."
                                    )
                    c_id = data["bot_communications_data"][key]["client_queue"].get(block=False)
                    del data["tick_updates"][update_key]
                    return ev3sim.simulation.comm_schema_pb2.GetClientResult(result=True, client_id=c_id, msg="")
                except KeyError:
                    if update_key in data["tick_updates"]:
                        del data["tick_updates"][update_key]
                    return ev3sim.simulation.comm_schema_pb2.GetClientResult(
                        result=False, client_id="N/A", msg="Your connection was closed."
                    )

            def RequestSend(self, request, context):
                rob_id = request.robot_id
                key = f"{request.address}:{request.port}"
                client_id = request.client_id
                d = request.data
                update_key = f"{rob_id}:RS"
                try:
                    if key not in data["bot_communications_data"] or (
                        data["bot_communications_data"][key]["server_id"] not in (rob_id, client_id)
                    ):
                        return ev3sim.simulation.comm_schema_pb2.SendResult(
                            result=False,
                            msg="Server on address does not exist, or the incorrect Robot ID was specified.",
                        )
                    if rob_id == data["bot_communications_data"][key]["server_id"]:
                        data_keys = (client_id, "recvs")
                    else:
                        data_keys = (rob_id, "sends")
                    if data_keys[0] not in data["bot_communications_data"][key]["connections"]:
                        return ev3sim.simulation.comm_schema_pb2.SendResult(
                            result=False,
                            msg="Server on address does not exist, or the incorrect Robot ID was specified.",
                        )
                    data["bot_communications_data"][key]["connections"][data_keys[0]][data_keys[1]].put(d)
                    # Wait for the request to be consumed.
                    last_tick = time.time()
                    data["tick_updates"][update_key] = Queue(0)
                    with data["bot_locks"][rob_id]["condition_waiting"]:
                        while True:
                            if not data["bot_communications_data"][key]["connections"][data_keys[0]][
                                data_keys[1]
                            ]._qsize():
                                del data["tick_updates"][update_key]
                                return ev3sim.simulation.comm_schema_pb2.SendResult(result=True, msg="")
                            data["bot_locks"][rob_id]["condition_waiting"].wait(TICK_WAITING_TIMEOUT)
                            try:
                                data["tick_updates"][update_key].get(timeout=TICK_WAITING_TIMEOUT)
                                last_tick = time.time()
                            except:
                                if result._qsize():
                                    return ev3sim.simulation.comm_schema_pb2.SendResult(
                                        result=False, msg="Simulation died."
                                    )
                except KeyError:
                    if update_key in data["tick_updates"]:
                        del data["tick_updates"][update_key]
                    return ev3sim.simulation.comm_schema_pb2.SendResult(result=False, msg="Your connection was closed.")

            def RequestRecv(self, request, context):
                rob_id = request.robot_id
                key = f"{request.address}:{request.port}"
                client_id = request.client_id
                update_key = f"{rob_id}:RR"
                try:
                    if key not in data["bot_communications_data"] or (
                        data["bot_communications_data"][key]["server_id"] not in (rob_id, client_id)
                    ):
                        return ev3sim.simulation.comm_schema_pb2.RecvResult(
                            result=False,
                            data="N/A",
                            msg="Server on address does not exist, or the incorrect Sender ID was specified.",
                        )
                    if rob_id == data["bot_communications_data"][key]["server_id"]:
                        data_keys = (client_id, "sends")
                    else:
                        data_keys = (rob_id, "recvs")
                    if data_keys[0] not in data["bot_communications_data"][key]["connections"]:
                        return ev3sim.simulation.comm_schema_pb2.RecvResult(
                            result=False,
                            data="N/A",
                            msg="Server on address does not exist, or the incorrect Sender ID was specified.",
                        )
                    last_tick = time.time()
                    data["tick_updates"][update_key] = Queue(0)
                    with data["bot_communications_data"][key]["connections"][data_keys[0]][data_keys[1]].not_empty:
                        while not data["bot_communications_data"][key]["connections"][data_keys[0]][
                            data_keys[1]
                        ]._qsize():
                            data["bot_communications_data"][key]["connections"][data_keys[0]][
                                data_keys[1]
                            ].not_empty.wait(TICK_WAITING_TIMEOUT)
                            try:
                                data["tick_updates"][update_key].get(timeout=TICK_WAITING_TIMEOUT)
                                last_tick = time.time()
                            except:
                                if result._qsize():
                                    return ev3sim.simulation.comm_schema_pb2.RecvResult(
                                        result=False, data="N/A", msg="Simulation died."
                                    )
                    d = data["bot_communications_data"][key]["connections"][data_keys[0]][data_keys[1]].get()
                    with data["bot_locks"][client_id]["condition_changing"]:
                        data["bot_locks"][client_id]["condition_waiting"].notify()
                    del data["tick_updates"][update_key]
                    return ev3sim.simulation.comm_schema_pb2.RecvResult(data=d, result=True, msg="")
                except KeyError:
                    if update_key in data["tick_updates"]:
                        del data["tick_updates"][update_key]
                    return ev3sim.simulation.comm_schema_pb2.RecvResult(
                        data="", result=False, msg="Your connection was closed."
                    )

            def CloseServerConnection(self, request, context):
                rob_id = request.robot_id
                key = f"{request.address}:{request.port}"
                if (
                    key not in data["bot_communications_data"]
                    or data["bot_communications_data"][key]["server_id"] != rob_id
                ):
                    return ev3sim.simulation.comm_schema_pb2.CloseServerResult(
                        result=False, msg="Server is already closed, or you are not the host of it."
                    )
                del data["bot_communications_data"][key]
                return ev3sim.simulation.comm_schema_pb2.CloseServerResult(result=True, msg="")

            def CloseClientConnection(self, request, context):
                rob_id = request.robot_id
                key = f"{request.address}:{request.port}"
                server_id = request.server_id
                if (
                    key not in data["bot_communications_data"]
                    or data["bot_communications_data"][key]["server_id"] != server_id
                ):
                    # If the server is closed, this isn't considered an error.
                    return ev3sim.simulation.comm_schema_pb2.CloseClientResult(
                        result=True, msg="Server you are connecting to is already closed."
                    )
                if rob_id not in data["bot_communications_data"][key]["connections"]:
                    return ev3sim.simulation.comm_schema_pb2.CloseClientResult(
                        result=False, msg="You don't have a connection with this server currently."
                    )
                # Delete send/receive data.
                del data["bot_communications_data"][key]["connections"][rob_id]
                # Delete client_queue elements.
                objs = []
                while data["bot_communications_data"][key]["client_queue"]._qsize():
                    try:
                        objs.append(
                            data["bot_communications_data"][key]["client_queue"].get(timeout=TICK_WAITING_TIMEOUT)
                        )
                    except:
                        pass
                if rob_id in objs:
                    objs.remove(rob_id)
                for obj in objs:
                    data["bot_communications_data"][key]["client_queue"].put(obj)
                return ev3sim.simulation.comm_schema_pb2.CloseClientResult(result=True, msg="")

        def serve():
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            ev3sim.simulation.comm_schema_pb2_grpc.add_SimulationDealerServicer_to_server(SimulationDealer(), server)
            server.add_insecure_port(bind_addr)
            server.start()
            server.wait_for_termination()

        logging.basicConfig()
        serve()
    except Exception as e:
        result.put(("Communications", e))
