#!/usr/bin/env python3

from threading import Thread
import time

from middleware import Middleware
from voice_capture import WhisperRecorder
from language_processor_names_only import LanguageProcessor
from name_letter_json_sender import NameLetterJsonSender
from c3 import C3MotorController


def main():
    middleware = Middleware()

    voice = WhisperRecorder(
        middleware=middleware,
        model_size="base",
        input_device=0,
        fp16=False,
        mic_channel=0
    )

    language = LanguageProcessor(middleware)

    name_sender = NameLetterJsonSender(
        middleware=middleware,
        excel_path="asl_static_right_hand_dataset.xlsx"
    )

    c3 = C3MotorController(
        middleware=middleware,
        i2c_address=0x41,
        frequency=50,
        letter_delay=1.0,
        name_delay=1.5
    )

    language_thread = Thread(
        target=language.run_loop,
        daemon=True
    )

    name_sender_thread = Thread(
        target=name_sender.run_loop,
        daemon=True
    )

    c3_thread = Thread(
        target=c3.run_loop,
        daemon=True
    )

    language_thread.start()
    name_sender_thread.start()
    c3_thread.start()

    print("""
System started.

Pipeline:
  Voice -> Language -> NameLetter -> C3 motors

Commands:
  s  -> start recording
  x  -> stop recording and transcribe
  p  -> print final name-letter JSON
  q  -> quit
""")

    try:
        while True:
            cmd = input("Command: ").strip().lower()

            if cmd == "s":
                voice.start_recording()

            elif cmd == "x":
                voice.stop_and_transcribe()

            elif cmd == "p":
                output = middleware.get_name_letters_output(clear=False)

                if output:
                    print("\nFinal JSON:")
                    print(output)
                else:
                    print("\nNo final JSON available yet.")

            elif cmd == "q":
                break

            else:
                print("Unknown command.")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nSystem stopped by user.")

    finally:
        voice.close()
        language.stop()
        c3.close()
        print("[Main] Closed.")


if __name__ == "__main__":
    main()
