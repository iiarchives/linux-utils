# Copyright (c) 2025 iiPython

# Modules
import json
from pathlib import Path

# Config handling
class Configuration:
    def __init__(self, file: Path | None = None) -> None:
        self.file = file or (Path.home() / ".config/agh-control/data.json")
        self.file.parent.mkdir(exist_ok = True)

        # Load existing data
        self.data = {}
        if self.file.is_file():
            self.data = json.loads(self.file.read_text())

    def save(self) -> None:
        self.file.write_text(json.dumps(self.data, indent = 4))

    def add_node(self, node: str, url: str, auth: str) -> None:
        if "nodes" not in self.data:
            self.data["nodes"] = {}

        if node not in self.data["nodes"]:
            self.data["nodes"][node] = {"url": url, "auth": auth}
            self.save()

    def del_node(self, node: str) -> None:
        if node in self.data.get("nodes", {}):
            del self.data["nodes"][node]
            self.save()

    def get_nodes(self) -> dict[str, dict[str, str]]:
        return self.data.get("nodes", {})

    def add_record(self, domain: str, address: str) -> None:
        if "records" not in self.data:
            self.data["records"] = {}

        self.data["records"][domain] = address
        self.save()

    def del_record(self, domain: str) -> None:
        if domain in self.data.get("records", {}):
            del self.data["records"][domain]
            self.save()

    def get_records(self) -> dict[str, str]:
        return self.data.get("records", {})
