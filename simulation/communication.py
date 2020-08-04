from concurrent import futures
import logging

import grpc

import simulation.comm_schema_pb2
import simulation.comm_schema_pb2_grpc
import collections
import json

def start_server_with_shared_data(data):

    class SimulationDealer(simulation.comm_schema_pb2_grpc.SimulationDealerServicer):

        def RequestTickUpdates(self, request, context):
            tick = 0
            rob_id = request.robot_id
            print(rob_id, " connected!")
            while True:
                if tick < data['tick']:
                    tick = data['tick']
                    # Change me to grab the shared data.
                    yield simulation.comm_schema_pb2.RobotData(tick=tick, content=json.dumps(data['robots'][rob_id]))
        
        def SendWriteInfo(self, request, context):
            rob_id = request.robot_id
            attribute_path = request.attribute_path
            value = request.value
            data['stack'].appendleft((rob_id, attribute_path, value))
            return simulation.comm_schema_pb2.WriteResult(result=True)

    def serve():
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        simulation.comm_schema_pb2_grpc.add_SimulationDealerServicer_to_server(SimulationDealer(), server)
        server.add_insecure_port('[::]:50051')
        server.start()
        server.wait_for_termination()

    logging.basicConfig()
    serve()