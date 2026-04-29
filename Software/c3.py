#!/usr/bin/env python3

import json
import time

import board
import busio
from adafruit_pca9685 import PCA9685


SERVOMIN = 150
SERVOMAX = 600

# Servo pins
THUMB_JOINT = 0
INDEX = 6
MIDDLE = 2
RING = 1
PINKY = 3
THUMB = 5
FOREARM = 4

ALL_PINS = [0, 1, 2, 3, 4, 5, 6]


class C3MotorController:
    def __init__(
        self,
        middleware,
        i2c_address=0x41,
        frequency=50,
        letter_delay=1.0,
        name_delay=1.5,
    ):
        self.middleware = middleware
        self.i2c_address = i2c_address
        self.frequency = frequency
        self.letter_delay = letter_delay
        self.name_delay = name_delay
        self.running = False

        i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(i2c, address=self.i2c_address)
        self.pca.frequency = self.frequency

        print("[C3] Motor controller initialized.")

    def clamp_angle(self, pin, angle):
        if pin in [0, 5]:
            return max(0, min(angle, 50))
        return max(0, min(angle, 120))

    def value_to_angle(self, pin, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0

        # Dataset uses values like -1, -0.75, 0.35.
        # Motor only needs magnitude: 1 -> 120 degrees, 0 -> 0 degrees.
        value = abs(value)
        value = max(0.0, min(value, 1.0))

        if pin in [0, 5]:
            return value * 50.0

        return value * 120.0

    def angle_to_pulse(self, angle):
        return int(SERVOMIN + (angle / 180.0) * (SERVOMAX - SERVOMIN))

    def set_servo(self, pin, angle):
        angle = self.clamp_angle(pin, angle)
        pulse = self.angle_to_pulse(angle)
        duty_cycle = int((pulse / 4096.0) * 65535)
        self.pca.channels[pin].duty_cycle = duty_cycle
        print(f"[C3] Pin {pin} -> {angle:.1f} degrees")
        return angle

    def reset_hand(self):
        for pin in ALL_PINS:
            self.set_servo(pin, 0)

    def key_to_pin(self, key):
        # Accept direct numeric pin headers: 0, 1, 2...
        try:
            pin = int(key)
            if pin in ALL_PINS:
                return pin
        except (TypeError, ValueError):
            pass

        normalized = str(key).strip().lower()

        # Your Excel uses right-hand joint names like R_Index, R_Middle, etc.
        name_to_pin = {
            "r_thumb_joint": THUMB_JOINT,
            "right_thumb_joint": THUMB_JOINT,
            "thumb_joint": THUMB_JOINT,
            "thumb joint": THUMB_JOINT,

            "r_index": INDEX,
            "right_index": INDEX,
            "index": INDEX,

            "r_middle": MIDDLE,
            "right_middle": MIDDLE,
            "middle": MIDDLE,

            "r_ring": RING,
            "right_ring": RING,
            "ring": RING,

            "r_pinky": PINKY,
            "right_pinky": PINKY,
            "pinky": PINKY,

            "r_thumb": THUMB,
            "right_thumb": THUMB,
            "thumb": THUMB,

            "r_forearm": FOREARM,
            "right_forearm": FOREARM,
            "forearm": FOREARM,
        }

        return name_to_pin.get(normalized)

    def move_values(self, values):
        self.reset_hand()

        for key, value in values.items():
            pin = self.key_to_pin(key)

            if pin is None:
                # Ignore non-servo columns like active flags, shoulders, biceps, etc.
                continue

            angle = self.value_to_angle(pin, value)
            self.set_servo(pin, angle)

    def process_json(self, json_text):
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            print("[C3] Invalid JSON received.")
            return False

        names = data.get("names", [])

        if not names:
            print("[C3] No names to sign.")
            return False

        for name_data in names:
            name = name_data.get("name", "")
            letters = name_data.get("letters", [])

            print(f"[C3] Signing name: {name}")

            for letter_data in letters:
                letter = letter_data.get("letter", "")
                values = letter_data.get("values", {})

                print(f"[C3] Moving letter: {letter}")
                self.move_values(values)

                time.sleep(self.letter_delay)

            self.reset_hand()
            time.sleep(self.name_delay)

        print("[C3] Finished motor sequence.")
        return True

    def run_loop(self, poll_interval=0.2):
        self.running = True
        print("[C3] Running. Waiting for name-letter JSON...")

        while self.running:
            json_text = self.middleware.get_name_letters_output(clear=True)

            if json_text:
                self.process_json(json_text)

            time.sleep(poll_interval)

    def stop(self):
        self.running = False
        self.reset_hand()

    def close(self):
        self.stop()
        self.pca.deinit()
        print("[C3] Closed.")


def main():
    from middleware import Middleware

    middleware = Middleware()
    controller = C3MotorController(middleware)

    try:
        controller.run_loop()

    except KeyboardInterrupt:
        print("\n[C3] Stopped by user.")

    finally:
        controller.close()


if __name__ == "__main__":
    main()
