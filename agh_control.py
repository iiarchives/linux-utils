#!/usr/bin/python3

# Copyright (c) 2025 iiPython
# CLI for managing DNS across an Adguard Home cluster

# Modules
import sys
import json
from pathlib import Path
from getpass import getpass
from base64 import b64encode
from urllib.request import Request, urlopen

# Initialization
__version__ = "0.2.0"

# Handle synchronization
class Node:
    def __init__(self, name: str, url: str, auth: str) -> None:
        self.name, self.url, self.auth = name, url, auth

    def request(self, endpoint: str, **kwargs) -> str:
        return urlopen(Request(
            f"{self.url}/control/rewrite/{endpoint}",
            headers = {
                "Authorization": f"Basic {self.auth}",
                "Content-Type": "application/json"
            },
            **kwargs
        )).read()

    def fetch_records(self) -> list[dict[str, str]]:
        return json.loads(self.request("list"))

    def delete_record(self, record: dict[str, str]) -> None:
        self.request("delete", method = "POST", data = json.dumps(record).encode())

    def add_record(self, record: dict[str, str]) -> None:
        self.request("add", method = "POST", data = json.dumps(record).encode())

def sync(nodes: list[Node], records: dict[str, str]) -> None:
    print("\033[90mAttempting to sync records")

    longest_node_name = len(max(nodes, key = lambda node: len(node.name)).name)
    for node in nodes:
        added, removed, updated = 0, 0, 0
        print(f"    {node.name}{' ' * (longest_node_name - len(node.name))}...", end = "", flush = True)

        # Load existing records from node
        existing_records = node.fetch_records()
        for record in existing_records:
            existing_answer = records.get(record["domain"])

            # Remove anything that doesn't match our database
            mismatched = existing_answer != record["answer"]
            if mismatched:
                if existing_answer is not None:
                    node.add_record(record | {"answer": existing_answer})
                    updated += 1

                else:
                    removed += 1

                node.delete_record(record)

        # Handle new records
        existing_records = {record["domain"]: record["answer"] for record in existing_records}
        for domain, answer in records.items():
            if domain in existing_records:
                continue

            node.add_record({"domain": domain, "answer": answer})
            added += 1

        print(f"\033[32m\tOK \033[90m(added: {added}, removed: {removed}, updated: {updated})")

def list_records(records: dict[str, str]) -> None:
    print("\033[34mDNS Records")

    longest_name = len(max(records.keys(), key = lambda x: len(x)))
    for domain, address in records.items():
        print(f"    \033[33m{domain}{' ' * (longest_name - len(domain))} \033[90m⇀ {address}")

# File storage
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

    def get_nodes(self) -> list[Node]:
        return [Node(k, v["url"], v["auth"]) for k, v in self.data.get("nodes", {}).items()]

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

def main() -> None:
    config = Configuration()

    # Begin matching command
    match sys.argv[1:]:
        case [] | ["help"]:
            print("\033[34mCommands")
            for command in ["help", "version", "node", "node add \033[33m<name>", "node del \033[33m<name>", "add \033[33m<domain> <address>", "del \033[33m<domain>", "list", "sync", "fetch"]:
                print(f"    \033[90mdns {command}")

            print("\n\033[34mCopyright (c) 2025 \033[33miiPython\033[0m")

        case ["version"]:
            print(f"\033[34magh-control v{__version__}\033[0m by \033[33miiPython\033[0m")
            print("\033[90mhttps://github.com/iiarchives/linux-utils\033[0m")

        case ["node"]:
            print("\033[34mCommands")
            print("    \033[90mdns node add \033[33m<name>\n    \033[90mdns node del \033[33m<name>\n")

            existing_nodes = config.get_nodes()
            if not existing_nodes:
                return print("\033[90mNo nodes are being managed yet.\033[0m")

            longest_name = len(max(existing_nodes, key = lambda x: len(x.name)).name)

            print("\033[34mManaged nodes")
            for node in existing_nodes:
                print(f"    \033[33m{node.name}{' ' * (longest_name - len(node.name))} \033[90m@ {node.url}")

        case ["node", "add", node_name]:
            existing_nodes = config.get_nodes()
            if node_name in [node.name for node in existing_nodes]:
                return print("\033[90mNothing changed.\033[0m")
            
            management_url = input("\033[34mManagement URL (https://ns.example.org): \033[33m")
            username = input("\033[34mAccount name: \033[33m")
            password = getpass("\033[34mPassword: ")

            config.add_node(node_name, management_url, b64encode(f"{username}:{password}".encode()).decode())
            print("\033[1F\033[32m✓ Node added!\033[0m")

        case ["node", "del", node_name]:
            existing_nodes = config.get_nodes()
            if node_name not in [node.name for node in existing_nodes]:
                return print("\033[90mNothing changed.\033[0m")
            
            config.del_node(node_name)
            print("\033[32m✓ Node removed!\033[0m")

        case ["list"]:
            records = config.get_records()
            if not records:
                return print("\033[90mNo records are being managed yet.\033[0m")

            list_records(records)

        case ["add", domain, address]:
            records = config.get_records()
            config.add_record(domain, address)

            print(f"\033[32m✓ Record {'updated' if domain in records else 'added'}!\033[0m")

            existing_nodes = config.get_nodes()
            if not existing_nodes:
                print("\033[90mSkipping sync due to lack of managed nodes.")

            sync(existing_nodes, config.get_records())

        case ["del", domain]:
            records = config.get_records()
            if domain not in records:
                return print("\033[90mNothing changed.\033[0m")

            config.del_record(domain)
            sync(config.get_nodes(), records)

        case ["sync"]:
            sync(config.get_nodes(), config.get_records())

        case ["fetch"]:
            print("\033[90mAttempting to fetch records")

            existing_nodes, existing_records = config.get_nodes(), {}
            longest_node_name = len(max(existing_nodes, key = lambda x: len(x.name)).name)

            for node in config.get_nodes():
                fetched_records = node.fetch_records()
                print(f"\033[90m    {node.name}{' ' * (longest_node_name - len(node.name))}...", end = "", flush = True)
                existing_records |= {record["domain"]: record["answer"] for record in fetched_records}

                print(f"\033[32m\tOK ({len(fetched_records)} record(s))")

            print()
            list_records(existing_records)

            # Manual, but it works
            config.data["records"] = existing_records
            config.save()

        case _:
            print("unrecognized command")

# Handle CLI
if __name__ == "__main__":
    main()
