#!/usr/bin/env python3
"""Source-mode check of the per-item debugger attach (GUI path).

The set_debug_attach control command must make a py_func item wait for a
debugger without any 'debug' attribute in the .tum, and stop doing so
once disabled. To stay deterministic the run uses a pip-less venv as
python_bin: debugpy cannot be there, so the attach fails immediately
with its install message instead of waiting for an IDE. Run by run.sh in
source mode.
"""
import io
import os
import sys
import shutil
import tempfile
import venv
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

TIMEOUT = 60

_capture = io.StringIO()
sys.stdout = _capture


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


def fail(msg):
    _emit(f"PY_FUNC ATTACH CHECK: FAIL — {msg}", fd=2)
    os._exit(1)


def flatten(tree, out):
    for item_id, node in tree.items():
        out[node["name"]] = item_id
        if node.get("child"):
            flatten(node["child"], out)


def run_once(ctrl, queue):
    ctrl.control("execute")
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        try:
            m = queue.get(timeout=0.2)
        except Empty:
            continue
        if isinstance(m, dict) and "id" in m and m["id"] is None:
            time.sleep(0.5)
            return m.get("success")
    fail("run did not finish in time")


def main():
    # Debug-port fallback: with the first port busy, the scan must pick
    # another one in the range.
    import socket
    from py_func import handle
    s = socket.socket()
    s.bind(("localhost", 0))
    busy = s.getsockname()[1]
    chosen = handle._pick_debug_port(busy)
    s.close()
    if chosen is None or chosen == busy:
        fail(f"port scan returned {chosen} while {busy} was busy")

    # Hold the port so the attach cannot block waiting for a client.
    # Interpreter without debugpy: the attach fails fast instead of
    # waiting for an IDE.
    venv_dir = tempfile.mkdtemp(prefix="testium_attach_venv_")
    venv.create(venv_dir, with_pip=False)
    py_bin = os.path.join(venv_dir, "bin", "python3")
    if not os.path.exists(py_bin):
        py_bin = os.path.join(venv_dir, "Scripts", "python.exe")

    test_file = os.path.join(HERE, "py_func_attach", "test.tum")
    msg_queue = Queue()
    ctrl = TestSetController()
    proc = TestProcess(test_file, msg_queue, ctrl, [],
                       {"python_bin": py_bin})
    proc.start()

    loaded = threading.Event()
    threading.Thread(
        target=lambda: (ctrl.control("loaded"), loaded.set()), daemon=True
    ).start()
    while not loaded.wait(timeout=0.1):
        if not proc.is_alive():
            fail("TestProcess died during load")

    ids = {}
    flatten(ctrl.control("tree"), ids)
    if "plain" not in ids:
        fail("fixture item 'plain' not found")

    # Attach requested from the GUI: the item must try to attach and fail
    # on the missing debugpy.
    ctrl.control("set_debug_attach", item_id=ids["plain"], enabled=True)
    mark = _capture.tell()
    if run_once(ctrl, msg_queue):
        fail("run 1: the item succeeded, attach was not requested")
    out = _capture.getvalue()[mark:]
    if "debug setup failed" not in out:
        fail(f"run 1: no debug-setup diagnostic in the log: {out[-300:]!r}")

    # Attach cancelled: back to a normal run.
    ctrl.control("set_debug_attach", item_id=ids["plain"], enabled=False)
    if not run_once(ctrl, msg_queue):
        fail("run 2: the item still failed after the attach was cancelled")

    if proc.is_alive():
        ctrl.control("close")
    proc.join(10)
    if proc.is_alive():
        proc.terminate()
    shutil.rmtree(venv_dir, ignore_errors=True)

    _emit("PY_FUNC ATTACH CHECK: PASS")
    os._exit(0)


if __name__ == "__main__":
    main()
