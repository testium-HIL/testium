#!/usr/bin/env python3
"""Per-channel check of test-load error reporting.

Given the channel's testium invocation as argv (e.g. ``flatpak run
--command=testium org.testium.Testium``, a PyInstaller binary path, or
``python -m testium``), load each deliberately broken ``.tum`` under
``load_errors/`` in batch mode and verify that:

  1. the load FAILS (non-zero exit), and
  2. the output carries the *specific, located* message we expect — not a bare
     Python traceback and not the generic 'crashed for any reason'.

This guards the load-time error handling in ``test_set.load_test_recursively``
and ``item_actions.load`` (a structural mistake in a ``.tum`` must always reach
the user as a readable ``TUM file syntax error`` naming the offending file,
item path and value). The historical failure mode was an unknown console
action crashing the error formatter itself with ``'dict_keys' object is not
subscriptable``.

Exits non-zero (with a diagnostic) on the first failure so the validation run
fails loudly. Used by ``run.sh`` before launching the main suite.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "load_errors")

# testium colourises its log; strip the ANSI escapes before matching messages.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# fixture file -> substrings that must all appear in the load output.
CASES = [
    ("unknown_item.tum",     ["TUM file syntax error", "is not a known test item",
                              "frobnicate", "Known items:"]),
    ("unknown_action.tum",   ["unknown action", "opens", "Known actions:"]),
    ("two_steps.tum",        ["must define exactly one test item"]),
    ("scalar_body.tum",      ["body of test item 'sleep'", "must be a mapping"]),
    ("group_no_steps.tum",   ["No 'steps' list found", "'group' item 'g'"]),
    ("step_not_mapping.tum",  ["is not a valid test item"]),
    # The error is inside the included file: the message must name that file.
    ("bad_include.tum",      ["bad_include_inc.tum", "frobnicate_in_include",
                              "is not a known test item"]),
]


def fail(msg):
    print(f"LOAD-ERROR CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


def check_case(cmd, fixture, needles):
    path = os.path.join(FIXTURES, fixture)
    try:
        out = subprocess.run(cmd + ["-b", path], capture_output=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        fail(f"`{' '.join(cmd)} -b {fixture}` could not run: {e}")
    blob = _ANSI.sub("", (out.stdout + out.stderr).decode(errors="replace"))

    if out.returncode == 0 or "Test run success." in blob:
        fail(f"{fixture}: load was expected to fail but succeeded "
             f"(exit {out.returncode}).")
    # A raw Python traceback reaching the user is exactly what we are guarding
    # against: every load error must be funnelled through a TUM*Error.
    if "Traceback (most recent call last)" in blob:
        fail(f"{fixture}: a raw Python traceback leaked to the user:\n"
             f"{blob[-600:]}")
    missing = [n for n in needles if n not in blob]
    if missing:
        fail(f"{fixture}: load message is missing {missing}.\n"
             f"--- got ---\n{blob[-800:]}")
    print(f"LOAD-ERROR CHECK: {fixture} OK")


def main():
    cmd = sys.argv[1:]
    if not cmd:
        fail("usage: load_errors_check.py <testium-invocation...>")
    for fixture, needles in CASES:
        check_case(cmd, fixture, needles)
    print("LOAD-ERROR CHECK: PASS")


if __name__ == "__main__":
    main()
