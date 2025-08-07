# Copyright (c) 2025 iiPython

# Modules
import re
import os
import sys
import tty
import shutil
import termios
import subprocess

# Initialization
if not shutil.which("ddcutil"):
    exit("ddcutil required for this script to work.")

value_regex = re.compile(r"current value = +(\d+)")
monitor_regex = re.compile(r"\/dev\/i2c-(\d).*\n.+\n.+\n[\w ]+: +(.*)\n +Model: +(.*)")

# Handle UI
class UI:
    def __init__(self) -> None:
        self.index = 1

        print("Loading display information...")
        self.displays = {
            int(number): {
                "manu": manufacturer,
                "model": model,
                "brightness": int(value_regex.findall(subprocess.check_output(
                    ["ddcutil", "getvcp", "10", "-d", number],
                    stderr = subprocess.DEVNULL,
                    text = True
                ))[0])  # type: ignore
            }
            for (number, manufacturer, model) in monitor_regex.findall(subprocess.check_output(["ddcutil", "detect"], stderr = subprocess.DEVNULL, text = True))
        }

    @staticmethod
    def read() -> int:
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        try:
            while True:
                b = os.read(sys.stdin.fileno(), 3).decode()
                return ord(b[2] if len(b) == 3 else b)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def update_brightness(self, display: int) -> None:
        subprocess.run(["ddcutil", "setvcp", "10", str(self.displays[display]["brightness"]), "-d", str(display)], stderr = subprocess.DEVNULL)

    def render(self) -> None:
        print("\033[2J\033[H", end = "")
        for number, data in self.displays.items():
            if number == self.index:
                print("\033[32m", end = "")

            print(f"{data['manu']} {data['model']}")
            active = round(40 * (data["brightness"] / 100))
            print(f"[{'#' * active}{' ' * (40 - active)}] {data['brightness']}%\033[0m\n")

        print("\nUp / Down | Left -5% / Right +5% | Enter to Apply | Q to Exit")

    def loop(self) -> None:
        while True:
            self.render()
            match self.read():
                case 10:
                    self.update_brightness(self.index)

                case 65 if self.index > 1:
                    self.index -= 1

                case 66 if self.index < len(self.displays):
                    self.index += 1

                case 67 if self.displays[self.index]["brightness"] < 100:
                    self.displays[self.index]["brightness"] += 5

                case 68 if self.displays[self.index]["brightness"] > 5:
                    self.displays[self.index]["brightness"] -= 5

                case 113:
                    break

UI().loop()
