from ev3dev2.sensor.lego import UltrasonicSensor
from ev3sim.code_helpers import CommClient

us = UltrasonicSensor(address="in3")
client = CommClient("aa:bb:cc:dd:ee:ff", 1234)

while True:
    client.send(str(us.distance_centimeters))
    print(f"Received: {client.recv(1024)}")
