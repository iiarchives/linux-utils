# Copyright (c) 2025 iiPython

# Modules
import sys
from getpass import getpass
from base64 import b64encode

from agh import __version__, config
from agh.node import NodeList
from agh.sync import sync

# Handle UI
def list_records(records: dict[str, str]) -> None:
    print("\033[34mDNS Records")

    longest_name = len(max(records.keys(), key = lambda x: len(x)))
    for domain, address in records.items():
        print(f"    \033[33m{domain}{' ' * (longest_name - len(domain))} \033[90m⇀ {address}")

# Handle CLI
def main() -> None:
    node_list = NodeList()
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

            existing_nodes = node_list.all()
            if not existing_nodes:
                return print("\033[90mNo nodes are being managed yet.\033[0m")

            longest = node_list.longest_name()

            print("\033[34mManaged nodes")
            for node in existing_nodes:
                print(f"    \033[33m{node.name}{' ' * (longest - len(node.name))} \033[90m@ {node.url}")

        case ["node", "add", node_name]:
            existing_nodes = config.get_nodes()
            if existing_nodes.get(node_name):
                return print("\033[90mNothing changed.\033[0m")
            
            management_url = input("\033[34mManagement URL (https://ns.example.org): \033[33m")
            username = input("\033[34mAccount name: \033[33m")
            password = getpass("\033[34mPassword: ")

            config.add_node(node_name, management_url, b64encode(f"{username}:{password}".encode()).decode())
            print("\033[1F\033[32m✓ Node added!\033[0m")

        case ["node", "del", node_name]:
            existing_nodes = config.get_nodes()
            if not existing_nodes.get(node_name):
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

            nodes = node_list.all()
            if not nodes:
                return print("\033[90mSkipping sync due to lack of managed nodes.")

            sync(nodes, config.get_records())

        case ["del", domain]:
            records = config.get_records()
            if domain not in records:
                return print("\033[90mNothing changed.\033[0m")

            config.del_record(domain)
            sync(node_list.all(), records)

        case ["sync"]:
            sync(node_list.all(), config.get_records())

        case ["fetch"]:
            print("\033[90mAttempting to fetch records")

            existing_nodes, existing_records = node_list.all(), {}
            longest = node_list.longest_name()

            for node in existing_nodes:
                fetched_records = node.get_records()
                print(f"\033[90m    {node.name}{' ' * (longest - len(node.name))}...", end = "", flush = True)
                existing_records |= {record["domain"]: record["answer"] for record in fetched_records}

                print(f"\033[32m\tOK ({len(fetched_records)} record(s))")

            print()
            list_records(existing_records)

            # Manual, but it works
            config.data["records"] = existing_records
            config.save()

        case _:
            print("unrecognized command")

if __name__ == "__main__":
    main()
