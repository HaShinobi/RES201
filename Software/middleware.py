#!/usr/bin/env python3

from threading import Lock


class Middleware:
    def __init__(self):
        self.lock = Lock()

        self.recognized_text = None
        self.language_output = None
        self.name_letters_output = None

    # -----------------------------
    # Voice Capture -> Language Processor
    # -----------------------------
    def set_recognized_text(self, value):
        with self.lock:
            self.recognized_text = value

    def get_recognized_text(self, clear=False):
        with self.lock:
            value = self.recognized_text

            if clear:
                self.recognized_text = None

            return value

    # -----------------------------
    # Language Processor -> Name Letter Processor
    # -----------------------------
    def set_language_output(self, value):
        with self.lock:
            self.language_output = value

    def get_language_output(self, clear=False):
        with self.lock:
            value = self.language_output

            if clear:
                self.language_output = None

            return value

    # -----------------------------
    # Name Letter Processor -> Next Stage
    # -----------------------------
    def set_name_letters_output(self, value):
        with self.lock:
            self.name_letters_output = value

    def get_name_letters_output(self, clear=False):
        with self.lock:
            value = self.name_letters_output

            if clear:
                self.name_letters_output = None

            return value

    # -----------------------------
    # Optional clear all
    # -----------------------------
    def clear_all(self):
        with self.lock:
            self.recognized_text = None
            self.language_output = None
            self.name_letters_output = None