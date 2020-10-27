from ev3sim.constants import *


class BotCommService:
    def __init__(self):
        self.servers = {}
        self.waiting_clients = []

    def serverAvailable(self, connection_string):
        return connection_string in self.servers

    def attemptConnectToServer(self, client_id, connection_string):
        if self.serverAvailable(connection_string):
            self.connectToServer(client_id, connection_string)
        else:
            self.waiting_clients.append((client_id, connection_string))

    def connectToServer(self, client_id, connection_string):
        self.servers[connection_string]["connections"].append(client_id)
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.queues[client_id][ScriptLoader.SEND].put(
            (
                SUCCESS_CLIENT_CONNECTION,
                {
                    "host_id": self.servers[connection_string]["host_id"],
                },
            )
        )
        ScriptLoader.instance.queues[self.servers[connection_string]["host_id"]][ScriptLoader.SEND].put(
            (
                NEW_CLIENT_CONNECTION,
                {
                    "client_id": client_id,
                },
            )
        )

    def startServer(self, connection_string, robot_id):
        self.servers[connection_string] = {
            "host_id": robot_id,
            "connections": [],
        }
        to_remove = []
        for i, (client_id, c_string) in enumerate(self.waiting_clients):
            if c_string == connection_string:
                self.connectToServer(client_id, c_string)
                to_remove.append(i)
        for idx in to_remove[::-1]:
            del self.waiting_clients[idx]
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.queues[robot_id][ScriptLoader.SEND].put((SERVER_SUCCESS, {}))

    def closeServer(self, connection_string, robot_id):
        assert self.serverAvailable(connection_string), "Server already closed."
        assert self.servers[connection_string]["host_id"] == robot_id, "You are not the host of this server."
        del self.servers[connection_string]

    def closeClient(self, connection_string, robot_id):
        assert self.serverAvailable(connection_string), "Server already closed."
        assert robot_id in self.servers[connection_string]["connections"], "You are not the connected to this server."
        self.servers[connection_string]["connections"].remove(robot_id)

    def handleSend(self, origin_id, post_id, connection_string, data):
        assert self.serverAvailable(connection_string), "Server not closed, or otherwise unavailable."
        assert (
            origin_id == self.servers[connection_string]["host_id"]
            and post_id in self.servers[connection_string]["connections"]
        ) or (
            post_id == self.servers[connection_string]["host_id"]
            and origin_id in self.servers[connection_string]["connections"]
        ), "Communications between robots should be between a server and client."
        from ev3sim.simulation.loader import ScriptLoader

        ScriptLoader.instance.queues[post_id][ScriptLoader.SEND].put(
            (
                RECV_DATA,
                {
                    "data": data,
                },
            )
        )
        ScriptLoader.instance.queues[origin_id][ScriptLoader.SEND].put((SEND_SUCCESS, {}))
