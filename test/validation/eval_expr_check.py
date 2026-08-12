#!/usr/bin/env python3
"""Source-mode check of the F1 expression tester round trip.

Drives a real TestProcess: eval_expr evaluates an expression against
the live global dict (nominal, $(var) expansion, error case). Run by
run.sh in source mode.
"""
import io
import os
import sys
import threading
from multiprocessing import Queue

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from runtime.tum_except import ETUMRuntimeError

# The child's stdout is echoed by a parent-side capture thread through
# print(): swallow it. Own messages go to the real fd.
sys.stdout = io.StringIO()


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


def fail(msg):
    _emit(f"EVAL-EXPR CHECK: FAIL — {msg}", fd=2)
    os._exit(1)


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

    res = ctrl.control("eval_expr", expr="<| 1 + 1 |>")
    if res != 2:
        fail(f"'<| 1 + 1 |>' evaluated to {res!r}, expected 2")

    ctrl.control("set_gd_var", name="expr_check_text", value="line1\nversion: 1.2.3")
    res = ctrl.control(
        "eval_expr",
        expr="<| re.search(r\"^version:\\s+\\d+\\.\\d+\\.\\d+$\", r'''$(expr_check_text)''', re.M) is not None |>")
    if res is not True:
        fail(f"multiline regex expression evaluated to {res!r}, expected True")

    try:
        ctrl.control("eval_expr", expr="<| 1 // 0 |>")
    except ETUMRuntimeError as e:
        if "ZeroDivisionError" not in str(e):
            fail(f"error message does not name the cause: {e}")
    else:
        fail("invalid expression did not raise")

    if proc.is_alive():
        ctrl.control("close")
    proc.join(10)
    if proc.is_alive():
        proc.terminate()

    _emit("EVAL-EXPR CHECK: PASS")
    os._exit(0)


if __name__ == "__main__":
    main()
