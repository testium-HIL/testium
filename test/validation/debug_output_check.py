#!/usr/bin/env python3
"""Source-mode check of the debug-output toggle plumbing.

Drives a real TestProcess through the control queue: run 1 without
test_debug produces no DEBUG lines; test_debug is then set through the
set_gd_var control command (the GUI toggle path); run 2 produces DEBUG
lines; after the run, test_debug is still set (STICKY_GD survives the
end-of-run restore_gd). Run by run.sh in source mode.
"""
import io
import os
import sys
import threading
import time
from queue import Empty
from multiprocessing import Queue

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController

TIMEOUT = 30

# The child's stdout is echoed by a parent-side capture thread through
# print(): collect it here. Own messages go to the real fd.
_capture = io.StringIO()
sys.stdout = _capture


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


def fail(msg):
    _emit(f"DEBUG-OUTPUT CHECK: FAIL — {msg}", fd=2)
    os._exit(1)


def wait_finished(queue):
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        try:
            m = queue.get(timeout=0.2)
        except Empty:
            continue
        if isinstance(m, dict) and "id" in m and m["id"] is None:
            time.sleep(0.5)   # let the stdout pipe drain
            return
    fail("run did not finish in time")


def main():
    test_file = os.path.join(HERE, "debug_output", "test.tum")
    msg_queue = Queue()
    ctrl = TestSetController()
    proc = TestProcess(test_file, msg_queue, ctrl, [], {})
    proc.start()

    loaded = threading.Event()
    threading.Thread(
        target=lambda: (ctrl.control("loaded"), loaded.set()), daemon=True
    ).start()
    while not loaded.wait(timeout=0.1):
        if not proc.is_alive():
            fail("TestProcess died during load")

    # Run 1: debug off — the fixture's per-item report processing prints
    # its details only in debug mode.
    mark = _capture.tell()
    ctrl.control("execute")
    wait_finished(msg_queue)
    out = _capture.getvalue()[mark:]
    if "DEBUG" in out:
        fail("run 1: DEBUG lines present with test_debug off")

    # GUI toggle path.
    ctrl.control("set_gd_var", name="test_debug", value=True)

    # Run 2: debug on.
    mark = _capture.tell()
    ctrl.control("execute")
    wait_finished(msg_queue)
    out = _capture.getvalue()[mark:]
    if "DEBUG" not in out:
        fail("run 2: no DEBUG line with test_debug on")

    # Sticky across the end-of-run restore_gd.
    gd = ctrl.control("get_gd_vars")
    if not gd.get("test_debug"):
        fail("test_debug lost after the run (restore_gd not sticky)")

    if proc.is_alive():
        ctrl.control("close")
    proc.join(10)
    if proc.is_alive():
        proc.terminate()

    _emit("DEBUG-OUTPUT CHECK: PASS")
    os._exit(0)


if __name__ == "__main__":
    main()
