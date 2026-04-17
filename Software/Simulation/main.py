import time
import serial
import mujoco
import mujoco.viewer

XML_PATH = "simulation.xml"
SERIAL_PORT = "COM7"
BAUD = 115200
SEND_HZ = 100
DEADBAND = 0.002
NUM_MOTORS = 9

def main():
    model = mujoco.MjModel.from_xml_path(XML_PATH)
    data = mujoco.MjData(model)

    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0)
    time.sleep(2.0)

    dt = 1.0 / SEND_HZ
    next_send = time.time()
    last_u_sent = None

    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            viewer.sync()

            u_vals = [float(data.ctrl[i]) for i in range(NUM_MOTORS)]

            now = time.time()
            if now >= next_send:
                should_send = (
                    last_u_sent is None or
                    any(abs(u_vals[i] - last_u_sent[i]) > DEADBAND for i in range(NUM_MOTORS))
                )

                if should_send:
                    msg = ",".join(f"{u:.4f}" for u in u_vals) + "\n"
                    ser.write(msg.encode("ascii"))
                    last_u_sent = u_vals.copy()

                next_send += dt

            mujoco.mj_step(model, data)

    ser.close()

if __name__ == "__main__":
    main()