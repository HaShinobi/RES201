import sounddevice as sd
import soundfile as sf
import keyboard
import numpy as np
import queue

SAMPLE_RATE = 44100
CHANNELS = 1
FILENAME = "test.wav"

audio_queue = queue.Queue()
recording = False
stream = None


def audio_callback(indata, frames, time_info, status):
    if recording:
        audio_queue.put(indata.copy())


def toggle_recording():
    global recording, stream

    if not recording:
        # START RECORDING
        print("🎙 Recording...")
        audio_queue.queue.clear()
        recording = True

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=audio_callback,
        )
        stream.start()

    else:
        # STOP RECORDING
        print("Stopped")
        recording = False
        stream.stop()
        stream.close()

        audio_data = []
        while not audio_queue.empty():
            audio_data.append(audio_queue.get())

        if audio_data:
            audio_np = np.concatenate(audio_data, axis=0)
            sf.write(FILENAME, audio_np, SAMPLE_RATE)
            print(f"Saved to {FILENAME}")
        else:
            print("No audio captured")


def main():
    print("Press SPACE to start/stop recording")
    print("Press ESC to quit")

    keyboard.on_press_key("space", lambda e: toggle_recording())
    keyboard.wait("esc")

    if recording:
        toggle_recording()

    print("Exiting")


if __name__ == "__main__":
    main()
