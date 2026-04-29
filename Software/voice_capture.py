#!/usr/bin/env python3

from threading import Lock, Thread
import time

import numpy as np
import sounddevice as sd
import whisper


SAMPLE_RATE = 16000
CHANNELS = 6
DTYPE = "int16"
BLOCKSIZE = 8000


class WhisperRecorder:
    def __init__(
        self,
        middleware,
        model_size="base",
        input_device=19,
        fp16=False,
        mic_channel=0,
    ):
        self.middleware = middleware

        self.model_size = model_size
        self.input_device = input_device
        self.fp16 = fp16
        self.mic_channel = mic_channel

        print(f"[Voice] Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        print("[Voice] Whisper model loaded.")

        self.lock = Lock()
        self.recording = False
        self.stream = None
        self.chunks = []

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Voice] Audio status: {status}")

        with self.lock:
            if self.recording:
                self.chunks.append(bytes(indata))

    def start_recording(self):
        with self.lock:
            if self.recording:
                print("[Voice] Already recording.")
                return False

            self.recording = True
            self.chunks = []

        try:
            self.stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCKSIZE,
                callback=self.audio_callback,
                device=self.input_device if self.input_device >= 0 else None,
            )
            self.stream.start()

        except Exception as e:
            with self.lock:
                self.recording = False

            print(f"[Voice] Failed to start stream: {e}")
            return False

        print(f"[Voice] Recording started on device {self.input_device}")
        return True

    def stop_and_transcribe(self):
        with self.lock:
            if not self.recording:
                print("[Voice] Not recording.")
                return False

            self.recording = False
            stream = self.stream
            chunks = self.chunks[:]
            self.stream = None

        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

        if not chunks:
            print("[Voice] No audio captured.")
            return False

        audio_float32 = self._prepare_audio(chunks)

        if audio_float32 is None:
            print("[Voice] Captured audio empty.")
            return False

        Thread(
            target=self._transcribe_and_send,
            args=(audio_float32,),
            daemon=True
        ).start()

        print("[Voice] Stopped. Transcription running.")
        return True

    def _prepare_audio(self, chunks):
        audio_bytes = b"".join(chunks)
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

        usable = (len(audio_int16) // CHANNELS) * CHANNELS
        audio_int16 = audio_int16[:usable]

        if usable == 0:
            return None

        audio_int16 = audio_int16.reshape(-1, CHANNELS)

        mic_channel = self.mic_channel
        if mic_channel < 0 or mic_channel >= CHANNELS:
            mic_channel = 0

        mono_int16 = audio_int16[:, mic_channel]
        audio_float32 = mono_int16.astype(np.float32) / 32768.0

        return audio_float32

    def _transcribe_and_send(self, audio_float32):
        print("[Voice] Transcribing...")

        try:
            result = self.model.transcribe(audio_float32, fp16=self.fp16)
            text = (result.get("text") or "").strip()
        except Exception as e:
            print(f"[Voice] Transcription failed: {e}")
            text = ""

        if text:
            print(f"[Voice] Transcript: {text}")

            # Send transcript to middleware
            self.middleware.set_recognized_text(text)

        else:
            print("[Voice] Transcript empty.")

    def close(self):
        with self.lock:
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass

            self.stream = None
            self.recording = False


def main():
    from middleware import Middleware

    middleware = Middleware()

    recorder = WhisperRecorder(
        middleware=middleware,
        model_size="base",
        input_device=19,
        fp16=False,
        mic_channel=0,
    )

    print("""
Commands:
  s  -> start recording
  x  -> stop and transcribe
  q  -> quit
""")

    try:
        while True:
            cmd = input("Command: ").strip().lower()

            if cmd == "s":
                recorder.start_recording()

            elif cmd == "x":
                recorder.stop_and_transcribe()

            elif cmd == "q":
                break

            else:
                print("Unknown command.")

            time.sleep(0.1)

    finally:
        recorder.close()


if __name__ == "__main__":
    main()