#!/usr/bin/env python3
"""Source-mode check: the presenter layer stays toolkit-free.

Walks the imports (AST) of src/testium/gui/** and of every
*_presenter.py under interpreter/test_items: no PySide/PyQt, no
main_win. Dialog presenters must not import gui/ either (they run in
spawned children with a minimal import surface). Run by run.sh in
source mode.
"""
import ast
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src", "testium"))

FORBIDDEN_GUI = ("PySide6", "PyQt5", "PyQt6", "main_win")
FORBIDDEN_DIALOG = FORBIDDEN_GUI + ("gui",)


def fail(msg):
    print(f"GUI PURITY CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


def imports_of(path):
    tree = ast.parse(open(path).read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def check(paths, forbidden, label):
    n = 0
    for path in paths:
        n += 1
        for mod in imports_of(path):
            root = mod.split(".")[0]
            if root in forbidden:
                fail(f"{label}: {os.path.relpath(path, SRC)} imports {mod}")
    return n


def main():
    n_gui = check(glob.glob(os.path.join(SRC, "gui", "**", "*.py"),
                            recursive=True),
                  FORBIDDEN_GUI, "gui/")
    if n_gui == 0:
        fail("no gui/ modules found")
    n_dlg = check(glob.glob(os.path.join(SRC, "interpreter", "test_items",
                                         "*_files", "*_presenter.py")),
                  FORBIDDEN_DIALOG, "dialog presenter")
    print(f"GUI PURITY CHECK: PASS ({n_gui} gui modules, "
          f"{n_dlg} dialog presenters)")


if __name__ == "__main__":
    main()
