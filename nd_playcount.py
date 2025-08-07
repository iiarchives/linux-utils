# Copyright (c) 2024 iiPython

# Modules
import sys
import sqlite3
from pathlib import Path

# Initialization
args = sys.argv[1:]
if not args:
    exit("usage: nd_playcount <database file>")

print("Please make sure you have Navidrome STOPPED before continuing.")
input("Press [ENTER] to continue.\n")

# Connect to database
connection = sqlite3.connect(Path(sys.argv[1]))
cursor = connection.cursor()

# Fetch our User ID
cursor.execute("SELECT user_id FROM annotation")
user_id = cursor.fetchone()[0]

# Iterate over albums
cursor.execute("SELECT id, name FROM album")

changed = False
for album_id, name in cursor.fetchall():

    # Calculate play count
    total_plays, play_dates = 0, []
    cursor.execute("SELECT id FROM media_file WHERE album_id=?", (album_id,))
    for (track_id,) in cursor.fetchall():
        cursor.execute("SELECT play_count, play_date FROM annotation WHERE item_id=?", (track_id,))
        results = cursor.fetchone()
        if results:
            total_plays += results[0]
            if results[1] is not None:
                play_dates.append(results[1])

    # Grab current play count
    cursor.execute("SELECT play_count FROM annotation WHERE item_id=?", (album_id,))
    result = cursor.fetchone()
    play_count = (result or [0])[0]

    # Check for a mismatch
    if play_count != total_plays:
        print(f"[+] {name} has {play_count} play(s) but correct number is {total_plays}")
        if result is not None:
            cursor.execute("UPDATE annotation SET play_count=? WHERE item_id=?", (total_plays, album_id))

        else:
            cursor.execute(
                "INSERT INTO annotation VALUES (?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    album_id,
                    "album",
                    total_plays,
                    max(play_dates),
                    0,
                    False,
                    None
                )
            )

        changed = True

if not changed:
    exit("[/] Nothing to do.")

connection.commit()
connection.close()

print(f"\n[+] Changes written to '{Path(args[0]).absolute()}'")
