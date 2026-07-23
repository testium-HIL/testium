"""External tool used by the `command` export validation item: dumps the
test names of a testium report database to a text file."""
import sqlite3
import sys


def main():
    db, out = sys.argv[1], sys.argv[2]
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT test_name FROM tests ORDER BY timestamp_start").fetchall()
    con.close()
    with open(out, "w", encoding="utf-8") as f:
        for (name,) in rows:
            f.write(name + "\n")


if __name__ == "__main__":
    main()
