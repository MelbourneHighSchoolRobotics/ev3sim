import numpy as np
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.devices.utils import NearestValue


class MotorMixin:

    THEORETICAL_MAX_FORCE = 10000
    # Possible multipliers for the theoretical maximum force.
    MIN_FORCE_PCT = 0.9
    MAX_FORCE_PCT = 1.05
    # How many fixed speeds the motors support (This is between +ve and negative, should be odd so that 0 is fixed).
    FIXED_SPEED_POINTS = 71

    time_wait = -1

    applied_force = 0

    device_type = "tacho-motor"
    command = "None"
    state = "holding"
    stop_action = "hold"
    time_sp = 0
    speed_sp = 0
    position_sp = 0
    counts_per_rot = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.state = "holding"
        self.stop_action = "hold"
        self.time_sp = 0
        self.speed_sp = 0
        self.position_sp = 0

    def generateBias(self):
        if ScriptLoader.RANDOMISE_SENSORS:
            self.MAX_FORCE = self.THEORETICAL_MAX_FORCE * (
                self.MIN_FORCE_PCT + self._interactor.random() * (self.MAX_FORCE_PCT - self.MIN_FORCE_PCT)
            )
        else:
            self.MAX_FORCE = self.THEORETICAL_MAX_FORCE
        self.speed_selection = NearestValue(
            -100, 100, self.FIXED_SPEED_POINTS if ScriptLoader.RANDOMISE_SENSORS else 201
        )

    def _updateTime(self, tick):
        if self.time_wait > 0:
            self.time_wait -= 1 / ScriptLoader.instance.GAME_TICK_RATE
            if self.time_wait <= 0:
                self.off()

    def _applyMotors(self, object, position, rotation):
        object.apply_force(self.applied_force * np.array([np.cos(rotation), np.sin(rotation)]), pos=position)

    def on(self, speed, **kwargs):
        """
        Turn the motors on indefinitely at a certain speed.

        :param float speed: Any number from -100 to 100. Negative values turn the motors the opposite direction.
        """
        assert -100 <= speed <= 100, "Speed value is out of bounds."
        speed = self.speed_selection.get_closest(speed) if speed >= 0 else -1 * self.speed_selection.get_closest(-speed)
        self.applied_force = speed * self.MAX_FORCE / 100
        # Ensure this overwrites further
        self.time_wait = -1
        self.state = "running"

    def on_for_seconds(self, speed, seconds, **kwargs):
        """
        Turn the motors on for a certain amount of time. Note that further calls to motors may interrupt this behaviour.

        :param float speed: Any number from -100 to 100. Negative values turn the motors the opposite direction.
        :param float seconds: Any positive number. Seconds the motors will stay this speed for.
        """
        self.on(speed, **kwargs)
        self.time_wait = seconds

    def on_for_rotations(self, speed, rotations, **kwargs):
        """
        Turn the motors on for a certain amount of rotations. Note that further calls to motors may interrupt this behaviour.

        :param float speed: Any number from -100 to 100. Negative values turn the motors the opposite direction.
        :param float rotations: Any number, amount of rotations to complete, Negative values will turn the motors the opposite direction.
        """
        if rotations < 0:
            speed *= -1
            rotations *= -1
        self.on_for_seconds(speed, rotations / self.ROTATIONS_PER_SECOND_AT_MAX * abs(speed) / 100, **kwargs)

    def on_for_degrees(self, speed, degrees, **kwargs):
        """
        Turn the motors on for a certain amount of degrees. Note that further calls to motors may interrupt this behaviour.

        :param float speed: Any number from -100 to 100. Negative values turn the motors the opposite direction.
        :param float degrees: Any number, amount of degrees to rotate, Negative values will turn the motors the opposite direction.
        """
        self.on_for_rotations(speed, degrees / 360)

    def off(self):
        """
        Turns the motors off indefinitely, until further calls are made.
        """
        self.applied_force = 0
        self.time_wait = -1
        self.state = "holding"

    def toObject(self):
        return {
            "address": self._interactor.port,
            "command": self.command,
            "count_per_rot": self.counts_per_rot,
            "driver_name": self.driver_name,
            "max_speed": 100,
            "speed_sp": self.speed_sp,
            "state": self.state,
            "stop_action": self.stop_action,
            "time_sp": self.time_sp,
        }

    def applyWrite(self, attribute, value):
        if attribute == "time_sp":
            self.time_sp = int(value)
        elif attribute == "speed_sp":
            self.speed_sp = float(value)
        elif attribute == "position_sp":
            self.position_sp = float(value)
        elif attribute == "stop_action":
            self.stop_action = value
        elif attribute == "command":
            if value == "run-forever":
                self.on(self.speed_sp, stop_action=self.stop_action)
            elif value == "run-timed":
                self.on_for_seconds(self.speed_sp, self.time_sp / 1000, stop_action=self.stop_action)
            elif value == "run-to-rel-pos":
                self.on_for_rotations(
                    self.speed_sp, self.position_sp / self.counts_per_rot, stop_action=self.stop_action
                )
            elif value == "stop":
                self.off()
            elif value == "reset":
                self.reset()
            else:
                raise ValueError(f"Unhandled write! {attribute} {value}")
        else:
            raise ValueError(f"Unhandled write! {attribute} {value}")
