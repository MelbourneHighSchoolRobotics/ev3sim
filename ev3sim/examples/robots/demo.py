"""
Some demo code for the ev3dev simulator.

This code will:
* print sensor values
* randomly move the motors every few seconds
* correct itself if it goes over the white line.
"""

from ev3dev2.motor import LargeMotor
from ev3dev2.sensor.lego import ColorSensor, UltrasonicSensor
from ev3dev2.sensor import Sensor
from ev3dev2.button import Button
from ev3sim.code_helpers import is_sim, EventSystem, wait_for_tick, robot_id


def handle_scored(data):
    if not data["against_you"]:
        print("I scored a goal!")


EventSystem.on_goal_scored = handle_scored

if is_sim:
    print(f"Hello from the simulator, from {robot_id}!!!")
else:
    print("Hello from the brick!!!")

import random
import time
from collections import deque

# When the up button is pressed, end the script.
end = False

buttons = Button()


def end_script(state):
    global end
    if state is True:
        end = True


buttons.on_up = end_script

# Some behavioural constants
STEP_LENGTH = (1, 3)  # Move in a new direction every 1-3 seconds
MOTOR_SPEEDS = (-100, 100)  # Motor values are anything between -100 and 100
PRINT_TIME = 5  # Print sensor values every 5 seconds


def random_between(a, b):
    # Returns a random float between a and b:
    return a + random.random() * (b - a)


# Initialise all sensors.
lm1 = LargeMotor(address="outB")
lm2 = LargeMotor(address="outC")
cs = ColorSensor(address="in2")
us = UltrasonicSensor(address="in3")
ir = Sensor(address="in1", driver_name="ht-nxt-ir-seek-v2")
compass = Sensor(address="in4", driver_name="ht-nxt-compass")
compass.command = "BEGIN-CAL"
compass.command = "END-CAL"

# This code moves in random directions, and stores the movements in a circular queue.
movement_queue = deque([], maxlen=5)
last_step_time = time.time()
last_print_time = time.time()
current_step_wait = 0
solving_white = False

while True:
    if time.time() - last_step_time > current_step_wait:
        # Set some new motor speeds, and a wait time.
        last_step_time = time.time()
        m1Speed, m2Speed = random_between(*MOTOR_SPEEDS), random_between(*MOTOR_SPEEDS)
        current_step_wait = random_between(*STEP_LENGTH)
        lm1.on_for_seconds(m1Speed, current_step_wait, block=False)
        lm2.on_for_seconds(m2Speed, current_step_wait, block=False)
        movement_queue.append(
            {
                "motor1Speed": m1Speed,
                "motor2Speed": m2Speed,
                "wait_time": current_step_wait,
            }
        )
        solving_white = False

    if time.time() - last_print_time > PRINT_TIME:
        # Print sensor values.
        last_print_time = time.time()
        # We add each line to a string so that we can print the lines all at
        # once, instead of one line at a time
        message = "Sensor Values\n"
        message += "=============\n"
        message += "Colour Sensor\n"
        message += f"RGB: {cs.rgb}\n"
        message += "Ultrasonic\n"
        message += f"Distance: {us.distance_centimeters}cm\n"
        message += "Infrared\n"
        message += f"Values: {[ir.value(x) for x in range(7)]}\n"
        message += "Compass\n"
        message += f"Bearing: {compass.value()}\n"
        message += "============="
        print(message)

    # If we hit the white line, then reverse this ongoing action
    # This white detection is bad, you should replace with something better (and more stable).
    if sum(cs.rgb) > 600 and not solving_white:
        # Reverse motor speeds, for the amount so far elapsed.
        elapsed = time.time() - last_step_time
        if len(movement_queue) > 0:
            movement = movement_queue.pop()
            # Set the last_step_time to now, and make sure we wait `elapsed` seconds.
            last_step_time = time.time()
            current_step_wait = elapsed
            lm1.on_for_seconds(-movement["motor1Speed"], elapsed, block=False)
            lm2.on_for_seconds(-movement["motor2Speed"], elapsed, block=False)
            # Set this so we don't infinitely back up.
            solving_white = True
    EventSystem.handle_events()

    buttons.process()
    wait_for_tick()

    if end:
        break
