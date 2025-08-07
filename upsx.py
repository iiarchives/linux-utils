#!/usr/bin/python3

# Copyright (c) 2025 iiPython
# upsx - replacement for NUT's ups-monitor

# Modules
import re
import time
import socket
import atexit
import logging
import subprocess

# Handle logging
logging.basicConfig(level = logging.INFO)
log = logging.getLogger("upsx")

__version__ = "0.2.5"
log.info(f"upsx version {__version__} is running.")

# Configuration
UPSD_TARGET   = "tripplite"   # The name of the UPS you want to track
UPSD_HOST     = "10.48.1.10"  # The IP address that UPSD is running on
UPSD_PORT     = 3493          # The port that UPSD is running on, most likely is set to default
UPSC_INTERVAL = 5             # Seconds to wait before polling
RUN_COMMAND   = [
    {
        # Specific keys from `upsc` that we're monitoring.
        "target": ["battery.charge", "ups.status"],

        # Lambda (or normal function) that is passed the value from our target,
        # and is responsible for returning a bool indicating if we should run our
        # commands or not.

        # Note that the value passed to this function will always be a string,
        # so you have to convert the value to whatever type you require.

        # In this case, are we lower then 25% battery?
        "check": lambda charge, status: int(charge) <= 25 and status not in ["OL", "OL CHRG"],

        # List of commands to run in order from top-down when our check returns `True`.
        "launch": [
            ["wall", "System is going down due to UPS reaching low battery!"],
            ["shutdown", "-P", "now"]
        ],

        # Indicate that the script should exit after this command fires,
        # prevents running commands twice (or more) with no debounce.
        "break": True
    }
]

# Handle communication with NUT
NUT_VARIABLE_REGEX = re.compile(r"VAR \w+ ([\w\.]+) \"(.+)\"")

class NUTCommunication:
    def __init__(self) -> None:
        self.connect()

    def connect(self) -> None:
        try:
            self.socket = socket.create_connection((UPSD_HOST, UPSD_PORT))
            self.file = self.socket.makefile("rwb", buffering = 0)

        except (OSError, ConnectionError):
            log.error("Failed to establish socket connection! Retrying in 10 seconds.")
            time.sleep(10)

            self.connect()

    def send_line(self, line: str) -> None:
        self.file.write((line + "\n").encode())

    def recv_line(self) -> str:
        return self.file.readline().decode().strip()

    def fetch_variables(self) -> dict[str, str]:
        self.send_line(f"LIST VAR {UPSD_TARGET}")

        # Process variables
        variables = {}
        while True:
            line = self.recv_line()
            if not line:
                log.error("Connection to NUT timed out, reestablishing socket.")
                self.connect()
                return self.fetch_variables()

            if line.startswith("END LIST VAR"):
                break

            line_data = NUT_VARIABLE_REGEX.match(line)
            if line_data is None:
                continue

            key, value = line_data.groups()
            variables[key] = value

        return variables

    def kill(self) -> None:
        self.send_line("LOGOUT")
        self.recv_line()
        self.socket.close()

        log.warning("Connection to NUT killed, daemon is exiting!")

NUT = NUTCommunication()
atexit.register(NUT.kill)

# Main event loop
while True:
    variables = NUT.fetch_variables()

    # Show a little status readout
    READOUT_INFO = [
        ("UPS", f"{variables['ups.model'].strip()} ({variables['ups.status']})"),
        ("Charge", f"{variables['battery.charge']}%"),
        ("Runtime", variables["battery.runtime"]),
        ("Input Voltage", f"{variables['input.voltage']}V"),
        ("Output Voltage", f"{variables['output.voltage']}V"),
        ("Battery Voltage", f"{variables['battery.voltage']}V"),
    ]
    log.info(" | ".join(f"{k}: {v}" for k, v in READOUT_INFO))

    # Handle launching commands
    for possible_command in RUN_COMMAND:
        command_result = possible_command["check"](*[variables.get(key) for key in possible_command["target"]])
        if command_result is not True:
            continue

        # Convert [a, b, c] to [[a, b, c]] in the event that we only have one launch command
        launch_data = possible_command["launch"]
        if isinstance(launch_data[0], str):
            launch_data = [launch_data]

        # And then actually launch everything
        for command in launch_data:
            subprocess.run(*command)

        if possible_command.get("break") is True:
            exit()

    time.sleep(UPSC_INTERVAL)
