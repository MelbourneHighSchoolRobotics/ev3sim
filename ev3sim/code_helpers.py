is_ev3 = True
is_sim = False

class CommServer:
    """
    Communications Server. Allows other bots to connect via a CommClient.
    """

    current_connection = None

    def __init__(self, hostAddress, port):
        """Initialise the communication server."""
        import bluetooth
        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.socket.bind((hostAddress, port))
        # Synchronous (1 Backlog)?
        self.socket.listen(1)
        self.clients = []

    def accept_client(self):
        """
        Wait for a client to connect, then return the client and client information

        If on ev3, this returns a bluetooth socket, as well as addr/port tuple.
        If on sim, this returns a mocked socket object, as well as addr/port tuple.
        """
        self.clients.append(self.socket.accept())
        return self.clients[-1]
    
    def close(self):
        for client in self.clients:
            client.close()
        self.socket.close()

class CommClient:
    """
    Communications Client. Can connect to other bots with CommServer running.
    """

    def __init__(self, hostAddress, port):
        """Initialise the connection."""
        import bluetooth
        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.socket.connect((hostAddress, port))
    
    def send(self, data):
        self.socket.send(data)
    
    def recv(self, limit):
        self.socket.recv(limit)

    def close(self):
        self.socket.close()
