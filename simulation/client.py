import logging
import grpc
import simulation.comm_schema_pb2
import simulation.comm_schema_pb2_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        print("Starting")
        stub = simulation.comm_schema_pb2_grpc.SimulationDealerStub(channel)
        response = stub.RequestTickUpdates(simulation.comm_schema_pb2.RobotRequest(robot_id='Robot-0'))
        for r in response:
            pass

logging.basicConfig()
run()