# Copyright (c) 2025 iiPython

# Modules
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agh import config, RequestError

# Handle class
class Node:
    def __init__(self, name: str, url: str, auth: str) -> None:
        self.name, self.url, self.auth = name, url, auth

    def request(self, endpoint: str, **kwargs) -> str:
        try:
            return urlopen(Request(
                f"{self.url}/control/rewrite/{endpoint}",
                headers = {
                    "Authorization": f"Basic {self.auth}",
                    "Content-Type": "application/json"
                },
                **kwargs
            )).read()

        except HTTPError as e:
            raise RequestError(e.code)

    def get_records(self) -> list[dict[str, str]]:
        return json.loads(self.request("list"))

    def del_record(self, record: dict[str, str]) -> None:
        self.request("delete", method = "POST", data = json.dumps(record).encode())

    def add_record(self, record: dict[str, str]) -> None:
        self.request("add", method = "POST", data = json.dumps(record).encode())

class NodeList:
    def __init__(self) -> None:
        pass

    def get(self, name: str) -> Node | None:
        nodes = config.get_nodes()
        return Node(name, **nodes[name]) if name in nodes else None

    def add(self, name: str, url: str, auth: str) -> None:
        config.add_node(name, url, auth)

    def rem(self, name: str) -> None:
        config.del_node(name)

    def all(self) -> list[Node]:
        return [
            Node(name, **node)
            for name, node in config.get_nodes().items()
        ]

    def longest_name(self) -> int:
        return len(max(self.all(), key = lambda x: len(x.name)).name)
