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


def main(shared_data, robot_file, robot_id):
    called_from = getcwd()
    shared_data["thread_ids"][threading.get_ident()] = robot_id
    def run_simulation():
        try:
            from ev3dev2 import Device, DeviceNotFound

            shared_data["write_blocking_ticks"][robot_id] = {}
            shared_data["last_checked_tick"][robot_id] = -1

            shared_data["tick_locks"][robot_id] = {
                "lock": threading.Lock()
            }
            shared_data["tick_locks"][robot_id]["cond"] = threading.Condition(shared_data["tick_locks"][robot_id]["lock"])

            def run_script(fname):
                from importlib.machinery import SourceFileLoader

                module = SourceFileLoader("__main__", fname).load_module()

            from ev3sim.file_helper import find_abs
            run_script(find_abs(robot_file, allowed_areas=["local", "local/robots/", "package", "package/robots/"]))
        except Exception as e:
            raise e

    run_simulation()

if __name__ == "__main__":
    main()
