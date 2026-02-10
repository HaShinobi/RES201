import time
import serial

import mujoco
import mujoco.viewer


# ---------- USER SETTINGS ----------
XML_PATH = "simulation.xml"

# Windows example: "COM4"
# macOS example: "/dev/tty.usbmodemXXXX"
# Linux example: "/dev/ttyACM0"
SERIAL_PORT = "COM8"
BAUD = 115200

SEND_HZ = 100           # how often we send slider values
DEADBAND = 0.002        # ignore tiny slider changes (0..1 scale)
# ----------------------------------


def main():
    model = mujoco.MjModel.from_xml_path(XML_PATH)
    data = mujoco.MjData(model)

    # Open serial to Arduino
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0)
    time.sleep(2.0)  # Arduino resets when serial opens

    dt = 1.0 / SEND_HZ
    next_send = time.time()

    last_u_sent = None

    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            mujoco.mj_step(model, data)

            # Slider value for actuator 0 (ensure your actuator ctrlrange is 0..1)
            u = float(data.ctrl[0])

            now = time.time()
            if now >= next_send:
                if (last_u_sent is None) or (abs(u - last_u_sent) > DEADBAND):
                    msg = f"{u:.4f}\n"
                    ser.write(msg.encode("ascii"))
                    last_u_sent = u
                next_send += dt

            viewer.sync()

    ser.close()


if __name__ == "__main__":
    main()
