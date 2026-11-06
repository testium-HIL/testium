#!/usr/bin/env python3
"""Source-mode check of the duration parser shared by sleep and plot
periodic. Run by run.sh in source mode."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

from interpreter.utils.duration import parse_duration  # noqa: E402
from runtime.tum_except import ETUMRuntimeError  # noqa: E402

ACCEPTED = [
    (10, 10.0),
    (1.5, 1.5),
    ("10", 10.0),
    ("1.5", 1.5),
    (" 3 ", 3.0),
    ("1h 3m 2s", 3782.0),
    ("2d", 172800.0),
    ("1.5h", 5400.0),
    ("1H30M", 5400.0),
    ("1d2h3m4s", 93784.0),
    ("0", 0.0),
]
REFUSED = ["1h30", "5m 3h", "10 minutes", "abc", "", "  ", -1, "-1", None,
           True, [1]]


def fail(msg):
    print(f"DURATION CHECK: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    for value, expected in ACCEPTED:
        got = parse_duration(value, "check")
        if got != expected:
            fail(f"{value!r}: got {got}, expected {expected}")
    for value in REFUSED:
        try:
            got = parse_duration(value, "check")
        except ETUMRuntimeError as e:
            if "check" not in str(e):
                fail(f"{value!r}: origin missing from message: {e}")
            continue
        fail(f"{value!r}: accepted as {got}, expected a refusal")
    print(f"DURATION CHECK: OK ({len(ACCEPTED)} accepted, "
          f"{len(REFUSED)} refused)")


if __name__ == "__main__":
    main()
