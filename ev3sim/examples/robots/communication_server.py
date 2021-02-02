"""
Example server code
Connect two clients to this server, and the server will relay information between the two.
"""
import time
from ev3sim.code_helpers import CommServer

# This address should be the actual address of the bluetooth receiver on the server bot.
server = CommServer("aa:bb:cc:dd:ee:ff", 1234)

print("Waiting for first client to connect")
client1, c1info = server.accept_client()
print("Waiting for second client to connect")
client2, c2info = server.accept_client()

print("Ready to receive!")

while True:
    # Swap the data around.
    c1data = client1.recv(1024)
    c2data = client2.recv(1024)
    client1.send(c2data)
    client2.send(c1data)

    time.sleep(1)
