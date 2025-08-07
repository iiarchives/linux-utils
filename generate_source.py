# Copyright (c) 2025 iiPython

# Modules
import textwrap

# Initialization
VERSION = "1.2"
FIELDS = {
    "version": {
        "size": 9
    },
    "type": {
        "name": "Type of content (Anime/TV/Movie/...)?",
        "size": 13
    },
    "name": {
        "name": "Name of content:",
        "size": 34
    },
    "year": {
        "name": "Year of content:",
        "size": 4
    },
    "added": {
        "name": "The original add date:",
        "size": 21
    },
    "modified": {
        "name": "Update date (N/A if not updated):",
        "size": 19
    },
    "vcodec": {
        "name": "Video codec:",
        "size": 8
    },
    "resolution": {
        "name": "Video resolution:",
        "size": 10
    },
    "vcomment": {
        "name": "Video comment (blank for N/A):",
        "size": 19
    },
    "acodec": {
        "name": "Audio codec:",
        "size": 8
    },
    "bitrate": {
        "name": "Audio bitrate (including 'kbps'):",
        "size": 10
    },
    "acomment": {
        "name": "Audio comment (blank for N/A):",
        "size": 19
    },
    "source": {
        "name": "Content source (blank for N/A):",
        "size": 43
    },
    "url": {
        "name": "Source URL (blank for N/A):",
        "size": 43
    },
    "torrent": {
        "name": "Torrent magnet (blank for N/A):",
        "size": 10000
    },
    "comment": {
        "name": "General comment (blank for N/A):",
        "size": 10000
    }
}

# Start asking questions
answers = {}
for field, data in FIELDS.items():
    if "name" not in data:
        continue

    while True:
        answers[field] = input(data["name"] + " ") or "N/A"
        if len(answers[field]) <= data["size"]:
            break

        print("Content too large, please retype.")

# UI handling
def pad(field: str, value: str | None = None) -> str:
    if value is None:
        value = str(answers[field])

    if field not in FIELDS:
        raise RuntimeError("The specified field was not found!")

    if field in ["torrent", "comment"]:
        return "\n".join(textwrap.TextWrapper(43).wrap(value))

    if len(value) > FIELDS[field]["size"]:
        raise RuntimeError("The content is too big to fit in the field!")

    return f"{value}{' ' * (FIELDS[field]['size'] - len(value))}"

# Build the torrent field
torrent = "\n".join([
    f"│ {line}{' ' * (43 - len(line))} │"
    for line in pad("torrent").split("\n")
])

# Build the comment field
comment = "\n".join([
    f"│ {line}{' ' * (43 - len(line))} │"
    for line in pad("comment").split("\n")
])

# Begin building the general file
built_file = f"""\
┌─ Info ──────────┬─ Version ─┬─ Category ────┐
│ iiPython Schema │ {pad('version', VERSION)} │ {pad('type')} │
├─ Name ──────────┴───────────┴──────┬─ Year ─┤
│ {pad('name')} │  {pad('year') }  │
├─ Added ───────────────┬─ Updated ──┴────────┤
│ {pad('added')} │ {pad('modified')} │
├─ Codec ──┬─ VR ───────┼─ Comments ──────────┤
│ {pad('vcodec')} │ {pad('resolution')} │ {pad('vcomment')} │
├─ Codec ──┼─ Bitrate ──┼─ Comments ──────────┤
│ {pad('acodec')} │ {pad('bitrate')} │ {pad('acomment')} │
├─ Source ─┴────────────┴─────────────────────┤
│ {pad('source')} │
├─ URL ───────────────────────────────────────┤
│ {pad('url')} │
├─ Torrent ───────────────────────────────────┤
{torrent}
├─ Comment ───────────────────────────────────┤
{comment}
└─────────────────────────────────────────────┘"""

print(built_file)
