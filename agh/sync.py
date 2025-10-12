# Copyright (c) 2025 iiPython

# Modules
from agh import RequestError
from agh.node import Node

# Handle synchronization
def sync(nodes: list[Node], records: dict[str, str]) -> None:
    print("\033[90mAttempting to sync records")

    longest_node_name = len(max(nodes, key = lambda node: len(node.name)).name)
    for node in nodes:
        added, removed, updated = 0, 0, 0
        print(f"    {node.name}{' ' * (longest_node_name - len(node.name))}...", end = "", flush = True)

        try:

            # Load existing records from node
            existing_records = node.get_records()
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

                    node.del_record(record)

            # Handle new records
            existing_records = {record["domain"]: record["answer"] for record in existing_records}
            for domain, answer in records.items():
                if domain in existing_records:
                    continue

                node.add_record({"domain": domain, "answer": answer})
                added += 1

            print(f"\033[32m\tOK \033[90m(added: {added}, removed: {removed}, updated: {updated})")

        except RequestError as e:
            print(f"\033[31m\tFAIL \033[90m(HTTP {e})")
