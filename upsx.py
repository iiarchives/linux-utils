#!/usr/bin/python3

# Copyright (c) 2025 iiPython
# upsx - replacement for NUT's ups-monitor

# Modules
import re
import sys
import time
import socket
import atexit
import logging
import subprocess

# Handle logging
logging.basicConfig(
    format = "[%(asctime)s] (%(levelname)s) %(message)s",
    datefmt = "%m/%d/%Y %H:%M:%S",
    level = logging.DEBUG if "-D" in sys.argv else logging.INFO
)
log = logging.getLogger("upsx")

__version__ = "0.2.8"

# Handle help menu
if "-h" in sys.argv or "--help" in sys.argv:
    print("upsx [-h, --help] [-D] [-v]")
    print("  -h:  show this message and exit")
    print("  -D:  enable debug logging")
    print("  -v:  print out all ups variables and exit")
    print(f"\nv{__version__}. https://github.com/iiarchives/linux-utils")
    exit()

log.info(f"upsx v{__version__} is running: https://github.com/iiarchives/linux-utils")

# Configuration
UPSD_TARGET   = "tripplite"   # The name of the UPS you want to track
UPSD_HOST     = "10.48.1.10"  # The IP address that UPSD is running on
UPSD_PORT     = 3493          # The port that UPSD is running on, most likely is set to default
LOCAL_PORT    = 0             # The port you want this client listening on, should probably leave this alone
LOCAL_HOST    = "0.0.0.0"     # The host you want this client listening on, ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UPSC_INTERVAL = 5             # Seconds to wait before polling
RUN_COMMAND   = [
    {
        # Specific keys from `upsc` that we're monitoring.
        "target": ["battery.charge", "ups.status"],

        # Lambda (or normal function) that is passed the value from our target,
        # and is responsible for returning a bool indicating if we should run our
        # commands or not.

        # Note that the values passed to this function will always be a string,
        # so you have to convert the values to whatever type you require.

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
            logging.info(f"Creating connection to {UPSD_HOST}:{UPSD_PORT} from {LOCAL_HOST}:{LOCAL_PORT}")

            self.socket = socket.create_connection((UPSD_HOST, UPSD_PORT), source_address = (LOCAL_HOST, LOCAL_PORT), timeout = 10)
            self.file = self.socket.makefile("rwb", buffering = 0)

        except (OSError, ConnectionError, TimeoutError):
            log.error("Failed to establish socket connection! Retrying in 10 seconds.")
            time.sleep(10)

            self.connect()

    def send_line(self, line: str) -> None:
        logging.debug(f"Sent through socket: {line}")
        self.file.write((line + "\n").encode())

    def recv_line(self) -> str:
        line = self.file.readline().decode().strip()
        logging.debug(f"Received line from socket: {line}")
        return line

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

if "-v" in sys.argv:
    variables = NUT.fetch_variables().items()
    biggest = len(max(variables, key = lambda k: len(k[0]))[0])
    for key, value in variables:
        print(f"  {key}{' ' * (biggest - len(key))}: {value}")

    exit()

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
            logging.debug(f"Running command: \"{' '.join(command)}\"")
            subprocess.run(command)

        if possible_command.get("break") is True:
            logging.debug("Killing daemon because the matched command has break enabled!")
            exit()

    time.sleep(UPSC_INTERVAL)
