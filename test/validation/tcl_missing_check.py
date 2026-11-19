#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Source-mode check of the behaviour when no Tcl interpreter is installed.

testium runs in batch mode with a PATH holding no tclsh:

  1. a test with a tcl_func item fails at load with a message naming the
     tried binaries and the 'tcl_bin' key, and no Python traceback;
  2. a test without tcl_func item runs normally.

Run by run.sh in source mode.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TESTIUM = os.path.abspath(os.path.join(HERE, "..", "..", "src", "testium"))
FIXTURES = os.path.join(HERE, "tcl_missing")

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fail(msg):
    print(f"TCL MISSING CHECK: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


TCL_NAMES = ("tclsh", "tclsh9.0", "tclsh8.6", "tclsh90", "tclsh86", "tclsh86t")


def path_without_tcl(tmp_dir):
    """PATH without any directory holding a tclsh. git is kept through a
    link in tmp_dir when its directory is dropped."""
    kept = [tmp_dir]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and not any(shutil.which(n, path=d) for n in TCL_NAMES):
            kept.append(d)
    path = os.pathsep.join(kept)
    git = shutil.which("git")
    if git and not shutil.which("git", path=path):
        try:
            os.symlink(git, os.path.join(tmp_dir, os.path.basename(git)))
        except OSError:
            print("TCL MISSING CHECK: SKIPPED: git and tclsh share a "
                  "directory and no link can be created")
            sys.exit(0)
    return path


def run(fixture, path):
    env = dict(os.environ, PATH=path)
    cmd = [sys.executable, TESTIUM, "-b", "-o",
           "-d", f"python_bin={sys.executable}",
           "--", os.path.join(FIXTURES, fixture)]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
    except Exception as e:  # noqa: BLE001
        fail(f"{fixture}: could not run testium: {e}")
    text = (out.stdout + out.stderr).decode("utf-8", errors="replace")
    # Wrapped messages: compare on single-spaced text.
    return out.returncode, " ".join(_ANSI.sub("", text).split())


def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = path_without_tcl(tmp_dir)
        rc, text = run("with_tcl.tum", path)
        if rc == 0:
            fail("with_tcl.tum: the load succeeded without Tcl")
        for needle in ("No valid Tcl 8.6+ interpreter found", "tclsh",
                       "'tcl_bin'"):
            if needle not in text:
                fail(f"with_tcl.tum: {needle!r} not in the output:\n{text}")
        if "Traceback" in text:
            fail(f"with_tcl.tum: Python traceback in the output:\n{text}")

        rc, text = run("without_tcl.tum", path)
        if rc != 0:
            fail(f"without_tcl.tum: the run failed without Tcl:\n{text}")
    print("TCL MISSING CHECK: OK")


if __name__ == "__main__":
    main()
