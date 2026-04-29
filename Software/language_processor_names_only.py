#!/usr/bin/env python3

import time
import json
from transformers import pipeline
import torch


class LanguageProcessor:
    def __init__(self, middleware):
        self.middleware = middleware

        print("[Language] Loading Gemma model...")
        self.pipe = pipeline(
            "text-generation",
            model="google/gemma-3-1b-it",
            device="cpu",
            torch_dtype=torch.float32
        )
        print("[Language] Gemma model loaded.")

        self.running = False

    def process_text(self, text):
        text = text.strip()

        if not text:
            print("[Language] Empty text received.")
            return None

        print(f"[Language] Received text: {text}")

        names = self.capture_names(text)

        if names.upper() == "NONE":
            names_list = []
        else:
            names_list = [
                name.strip()
                for name in names.split(",")
                if name.strip()
            ]

        message = {
            "names": names_list
        }

        json_message = json.dumps(message)

        print(f"[Language] JSON: {json_message}")

        self.middleware.set_language_output(json_message)

        return json_message

    def run_loop(self, poll_interval=0.2):
        self.running = True
        print("[Language] Running. Waiting for recognized text...")

        while self.running:
            text = self.middleware.get_recognized_text(clear=True)

            if text:
                self.process_text(text)

            time.sleep(poll_interval)

    def stop(self):
        self.running = False

    def capture_names(self, text):
        prompt = f"""Task: Find the human name or names and display them only. If there are no names, output NONE. End with <EOA>.

Input:
john jumped on the bridge and khalid watched him.
Output:
john,khalid<EOA>

Input:
the robot moved forward and stopped near the table.
Output:
NONE<EOA>

Input:
{text}
Output:
"""

        output = self.pipe(
            prompt,
            max_new_tokens=80,
            tokenizer=self.pipe.tokenizer,
            stop_strings=["<EOA>"],
            do_sample=False,
            return_full_text=False
        )

        names = output[0]["generated_text"]
        names = names.replace("<EOA>", "").strip()
        return names


def main():
    from middleware import Middleware

    middleware = Middleware()
    processor = LanguageProcessor(middleware)

    try:
        processor.run_loop()

    except KeyboardInterrupt:
        print("\n[Language] Stopped by user.")

    finally:
        processor.stop()


if __name__ == "__main__":
    main()
