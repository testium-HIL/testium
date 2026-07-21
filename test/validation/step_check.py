#!/usr/bin/env python3
"""Source-mode check of single-step execution (step_into/step_over/step_out).

Drives a real TestProcess through the control queue on a nested fixture and
asserts which item pauses after each step command, pinning the depth
semantics: into = next item at any depth, over = next item at depth <= ref,
out = next item at depth < ref. Run by run.sh in source mode.

Fixture (step_check/test.tum):
    main > A [s1, B [s2, s3], s4], s5, s6
"""
import os
import sys
import threading
from queue import Empty
from multiprocessing import Queue

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController

STEP_TIMEOUT = 10       # s: max wait for the expected "started" status
QUIESCENCE = 1.0        # s: silence required to consider execution paused


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


def fail(msg):
    _emit(f"STEP CHECK: FAIL — {msg}", fd=2)
    sys.exit(1)


def flatten(tree, out):
    for item_id, node in tree.items():
        out[node["name"]] = item_id
        if node.get("child"):
            flatten(node["child"], out)


class StatusReader:
    """Collects 'started' item names from the status queue."""

    def __init__(self, queue):
        self._q = queue
        self.finished = False
        self.success = None

    def _poll(self, timeout):
        try:
            m = self._q.get(timeout=timeout)
        except Empty:
            return None
        if "id" in m and m["id"] is None:
            self.finished = True
            self.success = m.get("success")
            return None
        if m.get("status") == "started":
            return m.get("name")
        return ""

    def next_started(self, timeout=STEP_TIMEOUT):
        """Next 'started' name within timeout, or None."""
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            got = self._poll(timeout=0.2)
            if got:
                return got
            if self.finished:
                return None
        return None

    def assert_quiet(self, ctx):
        got = self.next_started(timeout=QUIESCENCE)
        if got is not None:
            fail(f"{ctx}: expected pause, but '{got}' started")

    def wait_finished(self, timeout=STEP_TIMEOUT):
        import time
        deadline = time.monotonic() + timeout
        while not self.finished and time.monotonic() < deadline:
            self._poll(timeout=0.2)
        return self.finished


def main():
    test_file = os.path.join(HERE, "step_check", "test.tum")
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

    tree = ctrl.control("tree")
    ids = {}
    flatten(tree, ids)
    for name in ("A", "B", "s1", "s2", "s3", "s4", "s5", "s6"):
        if name not in ids:
            fail(f"item '{name}' not found in tree")

    reader = StatusReader(msg_queue)

    def expect_started(expected, ctx):
        got = reader.next_started()
        if got != expected:
            fail(f"{ctx}: expected '{expected}' to start, got {got!r}")

    # step_into sent before execute: run starts paused on the first item.
    ctrl.control("step_into")
    ctrl.control("execute")
    expect_started("Step check", "into from idle (root)")
    expect_started("A", "into from idle")
    reader.assert_quiet("into from idle")

    # Paused on A (depth 1). into -> s1 (depth 2).
    ctrl.control("step_into")
    expect_started("s1", "into A")
    reader.assert_quiet("into A")

    # Paused on s1 (depth 2). over -> next at depth <= 2: B.
    ctrl.control("step_over")
    expect_started("B", "over s1")
    reader.assert_quiet("over s1")

    # Paused on B (depth 2). over -> s2/s3 run through, next at depth <= 2: s4.
    ctrl.control("step_over")
    expect_started("s2", "over B (child runs)")
    expect_started("s3", "over B (child runs)")
    expect_started("s4", "over B")
    reader.assert_quiet("over B")

    # Paused on s4 (depth 2). out -> next at depth < 2: s5 (depth 1).
    ctrl.control("step_out")
    expect_started("s5", "out of A")
    reader.assert_quiet("out of A")

    # Paused on s5 (depth 1). Breakpoint on s6 + cont: breakpoint still works
    # and cont clears any pending step state.
    ctrl.control("add_breakpoint", item_id=ids["s6"])
    ctrl.control("cont")
    expect_started("s6", "cont to breakpoint")
    reader.assert_quiet("cont to breakpoint")

    # Paused on s6 (last item, depth 1). out at depth 1 -> run to completion.
    ctrl.control("step_out")
    if not reader.wait_finished():
        fail("run did not finish after step_out at top level")
    if reader.success is not True:
        fail(f"run finished with success={reader.success!r}")

    if proc.is_alive():
        ctrl.control("close")
    proc.join(10)
    if proc.is_alive():
        proc.terminate()
        fail("TestProcess did not exit")

    _emit("STEP CHECK: OK")


if __name__ == "__main__":
    main()
