#!/usr/bin/env python3
"""Source-mode check of the end-of-run global-dict restore.

Reproduces the GUI run loop: one backup_gd() at load, then restore_gd()
after each of three runs (process.py keeps a single backup for every run).
Nested dict/list globals must survive all three cycles, and the restored
values must never alias the backup (a later in-place clear would destroy
it). Run by run.sh in source mode.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

from interpreter.utils import globdict
from interpreter.utils.test_init import backup_gd, restore_gd


def fail(msg):
    print(f"GD-RESTORE CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


EXPECTED = [
    {"name": "choice 1", "choices": [{"name": "1.1"}, {"name": "1.2"}]},
    {"name": "choice 2"},
]

globdict.global_dict.clear()
globdict.global_dict.update({
    "menu": [
        {"name": "choice 1", "choices": [{"name": "1.1"}, {"name": "1.2"}]},
        {"name": "choice 2"},
    ],
    "params": {"path": "/tmp", "nested": {"depth": 2}},
})

backup = backup_gd()

for run in range(1, 4):
    # A run adds and mutates globals.
    globdict.global_dict["cs_dialog"] = ["choice 1"]
    globdict.global_dict["params"]["run"] = run
    restore_gd(backup)

    menu = globdict.global_dict.get("menu")
    if menu != EXPECTED:
        fail(f"after run {run}, 'menu' is {menu!r}")
    if globdict.global_dict["params"] != {"path": "/tmp", "nested": {"depth": 2}}:
        fail(f"after run {run}, 'params' is {globdict.global_dict['params']!r}")
    if "cs_dialog" in globdict.global_dict:
        fail(f"after run {run}, per-run global 'cs_dialog' survived the restore")
    if globdict.global_dict["menu"] is backup["menu"]:
        fail(f"after run {run}, restored 'menu' aliases the backup")

print("GD-RESTORE CHECK: PASS")
