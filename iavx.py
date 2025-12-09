#!/usr/bin/python3
# iiPython AV1 Encoding Tool - IAVx v1.7

# Modules
import sys
import json
import typing
import subprocess
from pathlib import Path

from rich.live import Live
from rich.console import Console
from rich.progress import MofNCompleteColumn, SpinnerColumn, TimeElapsedColumn, Progress

# Initialization
ENCODE_VERSION = "7"
COMMAND_ARGUMENTS = [
    "ffmpeg",
    "-analyzeduration", "500M",
    "-probesize"      , "500M",

    # Shut the fuck up
    "-hide_banner",
    "-stats",

    # Handle input control
    "-i"  ,     "%i",
    "-map",     "0",

    # Video encoding
    "-c:v"    , "libsvtav1",
    "-preset" , "%p",
    "-crf"    , "%c",
    "-aq-mode", "2" ,
    "-g"      , "%g",        # GOP, 10 times framerate, max 300
    "-vf"     , "showinfo",

    # 10 bit color encoding
    "-pix_fmt", "yuv420p10le",

    # Audio encoding
    "-c:a"  , "libopus",  # Encode both tracks as opus

    # Extra stages
    "-c:s", "copy",       # Direct copy each sub track
    "-y"  ,               # Force overwrite without asking

    # Tag the file in case of later analysis
    "-metadata", f"comment=Encoded by iiPython (v1.{ENCODE_VERSION}) w/ AV1 + OPUS.",
    "%o"
]

class IAVx:
    def __init__(self, target: Path, console: Console) -> None:
        self.settings, self.console, self.debug = {}, console, "--debug" in sys.argv

        # Probe given target
        try:
            self.console.print("[bright_black]Probing for media information...")
            self.file_info = self.probe_target(target)
        
        except ValueError as e:
            self.console.print(f"[red]  -> {e}")
            return exit(1)

        # Show file information
        selected_file = self.file_info[0][1]
        self.console.print(f"[yellow]  -> Video: {selected_file['video'][0]}p, {selected_file['video'][1]} fps, {selected_file['video'][2]}")
        for index, codec, sfmt, srate, channels, title in selected_file["audio"]:
           self.console.print(f"[yellow]  -> Audio #{index}: {codec}, {sfmt} bit/{srate} Hz, {channels} ({title})")

        # Begin the encoding process
        self.console.print()

    def encode_all(self, settings: dict[str, str]) -> None:
        self.settings = settings
        [self.encode_file(file, metadata) for file, metadata in self.file_info]

    @staticmethod
    def probe_file(file: Path) -> dict[str, typing.Any]:
        return json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_entries", "format=duration", "-show_streams", file],
            text = True
        ))

    @staticmethod
    def scan_files(target: Path) -> list[Path]:
        return sorted(
            (file for file in target.iterdir() if "iipython" not in file.name.lower()),
            key = lambda file: file.name
        )

    @staticmethod
    def probe_target(target: Path) -> list[tuple[Path, dict[str, tuple]]]:
        file_info = []
        for file in IAVx.scan_files(target):
            file_data = IAVx.probe_file(file)

            # Find stream info
            video_streams = [s for s in file_data["streams"] if s["codec_type"] == "video"]
            if not video_streams:
                raise ValueError("At least one file is missing a video stream, cannot continue!")

            if len(video_streams) > 1:
                raise ValueError("At least one file contains multiple video streams. This is unsupported and we cannot continue!")

            # Process st ream info
            video_stream = video_streams[0]
            file_info.append((file, {
                "video": (
                    video_stream["height"],
                    round((lambda x, y: x / y)(*[int(x) for x in video_stream["avg_frame_rate"].split("/")]), 2),  # type: ignore
                    video_stream["codec_name"].upper(),
                    int(float(file_data["format"]["duration"]))
                ),
                "audio": [
                    (index + 1, audio["codec_name"].upper(), audio["sample_fmt"][1:], audio["sample_rate"], audio["channel_layout"], audio.get("tags", {}).get("title", "untitled"))
                    for index, audio in enumerate([s for s in file_data["streams"] if s["codec_type"] == "audio"])
                ]
            }))
        
        return file_info

    def encode_file(self, file: Path, metadata: dict[str, typing.Any]) -> None:
        output_file = file.with_name(f"{file.with_suffix('').name} (iiPython v{ENCODE_VERSION})").with_suffix(".mkv")
        if output_file.is_file():
            return  # File already encoded

        # Process command arguments
        arguments = COMMAND_ARGUMENTS.copy()
        for key, value in {
            "i": file,
            "o": output_file,
            "g": round(metadata["video"][1] * 10),
            "c": self.settings["crf"],
            "p": self.settings["preset"]
        }.items():
            arguments[arguments.index(f"%{key}")] = str(value)

        if self.settings["ivtc"].lower() in ["yes", "y"]:
            arguments[arguments.index("showinfo")] += ",yadif=mode=0:parity=tff,fieldmatch=order=tff,decimate"

        if self.debug:
            index = 0
            while index <= len(arguments):
                argument, next_argument = arguments[index], " "
                if index < len(arguments) - 1:
                    next_argument = arguments[index + 1]

                self.console.print(f"[bright_black]\\[Debug, Command] {argument} {next_argument if next_argument[0] != '-' else ''}", highlight = False, emoji = False)
                index += 2 if next_argument[0] != "-" else 1

            self.console.print()

        # Launch FFmpeg
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            MofNCompleteColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task(f"[cyan]Encoding [bold]{file.name}", total = metadata["video"][-1])

            # Begin encoding
            with subprocess.Popen(arguments, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, text = True) as process, Live() as live:
                if process.stdout is None:
                    raise RuntimeError("No stdout object returned by Popen!")

                try:
                    for line in process.stdout:
                        line = line.strip()

                        # Handle FFmpeg errors
                        if "setting option" in line:
                            raise KeyboardInterrupt(f"FFmpeg exception: \\{line}")

                        # Log every line in debug mode
                        if self.debug:
                            self.console.print(f"  [bright_black]\\[Debug, FFmpeg] {line.removesuffix('\n')}")

                        # Check progress
                        if "pts_time" in line:
                            progress.update(task, completed = round(float(line.split("pts_time:")[1].split("duration")[0].strip())))

                        if "elapsed=" in line and "showinfo" not in line:
                            live.update(f"  [bright_black]-> {line}")

                    progress.update(task, completed = metadata["video"][-1], description = f"[green]Encoded {file.name}")
                    [live.stop() for live in (progress, live)]

                except KeyboardInterrupt as e:
                    process.kill()
                    if output_file.is_file():
                        output_file.unlink()

                    [live.stop() for live in (progress, live)]
                    self.console.print(f"{f'[red]{e}\n' if str(e) else '\n'}[red][bold]Encoding canceled.[/] Any unfinished encodes have been deleted.", highlight = False)

                    return exit(1)

if __name__ == "__main__":
    console = Console()
    console.print(f"[bold blue]iiPython AV1 Encoding System v1.{ENCODE_VERSION}\n")

    # Initialization
    iavx = IAVx(Path(sys.argv[1]), console)

    # Process settings
    settings = {}
    for id, name, default in [("preset", "SVT-AV1 Preset", "4"), ("crf", "CRF", "28"), ("ivtc", "Inverse Telecine?", "no")]:
        value = console.input(f"[bold yellow]{name} ({default}) -> ") or default

        # Overwrite previous line
        print("\033[1F", end = "")
        console.print(f"[bold yellow]{name} ({default}) -> [bright_black]{value}")

        settings[id] = value

    print()

    # Fetch audio channel settings
    for index in range(len(iavx.file_info[0][1]["audio"])):
        console.print(f"[bold yellow]Audio Track #{index + 1}")
    
        channels = console.input(f"  [bright_black]-> Channel Count: ")
        audio_index = COMMAND_ARGUMENTS.index("libopus") + 1

        # Add in ac parameter
        COMMAND_ARGUMENTS.insert(audio_index, f"-ac:a:{index}")
        COMMAND_ARGUMENTS.insert(audio_index + 1, channels)

        # Overwrite previous line
        print("\033[1F\033[2K\r", end = "")
        console.print(f"  [bright_black]-> Channel Count: {channels}")

        # Ask for title
        title = console.input(f"  [bright_black]-> Track Title (leave as-is): ")
        if title.strip():
            COMMAND_ARGUMENTS.insert(audio_index + 2, f"-metadata:s:a:{index}")
            COMMAND_ARGUMENTS.insert(audio_index + 3, f"title={title}")

        # Overwrite previous line
        print("\033[1F\033[2K\r", end = "")
        console.print(f"  [bright_black]-> Track Title: {title or 'leave as-is'}\n")

    print()
    iavx.encode_all(settings)
