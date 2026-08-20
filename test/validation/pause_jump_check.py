#!/usr/bin/env python3
"""Source-mode check of run-level pause, jump and conditional breakpoints.

Drives a real TestProcess through the control queue and asserts, from the
status stream, that: pause lets the current step finish and stops the run
before the next one (linear and inside a cycle); jump_to moves execution
forward and backward without running the interval and pauses on the target;
jump_back returns to the last executed step; a breakpoint condition gates
the pause; set_enabled_state applies during a paused run. Run by run.sh in
source mode.

Fixture (pause_jump/test.tum):
    main > A [slow(1.5s), s1], B [s2, s3], C(loop x2)[slowc(0.8s), c1], s5, s6
"""
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
from runtime.tum_except import ETUMRuntimeError

STEP_TIMEOUT = 15       # s: max wait for an expected status
QUIESCENCE = 1.0        # s: silence required to consider execution paused


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


def fail(msg):
    _emit(f"PAUSE-JUMP CHECK: FAIL — {msg}", fd=2)
    sys.exit(1)


def flatten(tree, out):
    for item_id, node in tree.items():
        out[node["name"]] = item_id
        if node.get("child"):
            flatten(node["child"], out)


class StatusReader:
    """Collects (status, name) events from the status queue."""

    def __init__(self, queue):
        self._q = queue
        self.finished = False
        self.success = None
        self.events = []

    def _poll(self, timeout):
        try:
            m = self._q.get(timeout=timeout)
        except Empty:
            return None
        if "id" in m and m["id"] is None:
            self.finished = True
            self.success = m.get("success")
            return None
        if m.get("status") in ("started", "paused"):
            ev = (m["status"], m.get("name"))
            self.events.append(ev)
            return ev
        return None

    def next_event(self, wanted, timeout=STEP_TIMEOUT):
        """Wait for a (status, name) event; return it or None."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ev = self._poll(timeout=0.2)
            if ev == wanted:
                return ev
            if self.finished:
                return None
        return None

    def expect(self, status, name, ctx):
        if self.next_event((status, name)) is None:
            fail(f"{ctx}: expected ({status}, {name}), events={self.events}")

    def assert_quiet(self, ctx):
        deadline = time.monotonic() + QUIESCENCE
        while time.monotonic() < deadline:
            ev = self._poll(timeout=0.2)
            if ev is not None and ev[0] == "started":
                fail(f"{ctx}: expected pause, but '{ev[1]}' started")

    def wait_finished(self, ctx, timeout=STEP_TIMEOUT):
        deadline = time.monotonic() + timeout
        while not self.finished and time.monotonic() < deadline:
            self._poll(timeout=0.2)
        if not self.finished:
            fail(f"{ctx}: run did not finish, events={self.events}")

    def new_run(self):
        self.finished = False
        self.success = None
        self.events = []


def main():
    test_file = os.path.join(HERE, "pause_jump", "test.tum")
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

    ids = {}
    flatten(ctrl.control("tree"), ids)
    for name in ("A", "B", "C", "slow", "s1", "s2", "s3", "c1", "s5", "s6"):
        if name not in ids:
            fail(f"item '{name}' not found in tree")

    reader = StatusReader(msg_queue)

    # --- Run 1: pause lets the current step finish, stops before the next.
    ctrl.control("execute")
    reader.expect("started", "slow", "run 1")
    ctrl.control("pause")
    reader.expect("started", "s1", "run 1: next step starts")
    reader.expect("paused", "s1", "run 1: next step pauses")
    reader.assert_quiet("run 1: paused on s1")
    ctrl.control("cont")
    # Same inside the cycle: pause during slowc, c1 pauses.
    reader.expect("started", "slowc", "run 1: cycle")
    ctrl.control("pause")
    reader.expect("paused", "c1", "run 1: cycle pause")
    reader.assert_quiet("run 1: paused on c1")
    ctrl.control("cont")
    reader.wait_finished("run 1")
    if reader.success is not True:
        fail(f"run 1 finished with success={reader.success!r}")

    # --- Run 2: jump forward, jump backward, jump_back without history.
    reader.new_run()
    ctrl.control("step_into")
    ctrl.control("execute")
    reader.expect("paused", "A", "run 2: into from idle")
    ctrl.control("jump_to", item_id=ids["s5"])
    reader.expect("paused", "s5", "run 2: jump forward")
    for status, name in reader.events:
        if status == "started" and name in ("slow", "s1", "s2", "s3", "c1"):
            fail(f"run 2: '{name}' ran during the forward jump")
    reader.assert_quiet("run 2: paused on s5")
    ctrl.control("jump_to", item_id=ids["s2"])
    reader.expect("started", "B", "run 2: backward jump enters B")
    reader.expect("paused", "s2", "run 2: jump backward")
    reader.assert_quiet("run 2: paused on s2")
    # No leaf body ran yet in this run: jump_back must refuse.
    try:
        ctrl.control("jump_back")
        fail("run 2: jump_back accepted with no executed step")
    except ETUMRuntimeError:
        pass
    ctrl.control("cont")
    reader.wait_finished("run 2")
    if reader.success is not True:
        fail(f"run 2 finished with success={reader.success!r}")

    # --- Run 3: conditional breakpoints + checkbox while paused.
    reader.new_run()
    ctrl.control("add_breakpoint", item_id=ids["s3"], condition="<| False |>")
    ctrl.control("add_breakpoint", item_id=ids["s5"], condition="<| True |>")
    ctrl.control("execute")
    reader.expect("paused", "s5", "run 3: true condition pauses")
    for status, name in reader.events:
        if status == "paused" and name == "s3":
            fail("run 3: false breakpoint condition paused")
    ctrl.control("set_enabled_state", item_id=ids["s6"], enabled_state=False)
    ctrl.control("cont")
    reader.wait_finished("run 3")
    for status, name in reader.events:
        if status == "started" and name == "s6":
            fail("run 3: s6 ran after being unchecked while paused")
    ctrl.control("del_breakpoint", item_id=ids["s3"])
    ctrl.control("del_breakpoint", item_id=ids["s5"])
    ctrl.control("set_enabled_state", item_id=ids["s6"], enabled_state=True)

    # --- Run 4: jump_back re-executes the last step, pauses on the next.
    reader.new_run()
    ctrl.control("add_breakpoint", item_id=ids["s2"])
    ctrl.control("execute")
    reader.expect("paused", "s2", "run 4: breakpoint")
    ctrl.control("jump_back")
    reader.expect("started", "s1", "run 4: last step re-executes")
    reader.expect("paused", "B", "run 4: pause on the next item")
    reader.assert_quiet("run 4: paused on B")
    ctrl.control("del_breakpoint", item_id=ids["s2"])
    ctrl.control("cont")
    reader.wait_finished("run 4")
    if reader.success is not True:
        fail(f"run 4 finished with success={reader.success!r}")

    # --- Run 5: jump_back across a finished cycle re-enters it (the last
    # executed leaf is c1 of iteration 2; C restarts at iteration 1).
    reader.new_run()
    ctrl.control("add_breakpoint", item_id=ids["s5"])
    ctrl.control("execute")
    reader.expect("paused", "s5", "run 5: breakpoint after the cycle")
    ctrl.control("jump_back")
    reader.expect("started", "C", "run 5: jump_back re-enters the cycle")
    reader.expect("started", "c1", "run 5: last cycle leaf re-executes")
    reader.expect("paused", "slowc", "run 5: pause on the next item")
    reader.assert_quiet("run 5: paused on slowc")
    ctrl.control("del_breakpoint", item_id=ids["s5"])
    ctrl.control("cont")
    reader.wait_finished("run 5")
    if reader.success is not True:
        fail(f"run 5 finished with success={reader.success!r}")

    if proc.is_alive():
        ctrl.control("close")
    proc.join(10)
    if proc.is_alive():
        proc.terminate()
        fail("TestProcess did not exit")

    _emit("PAUSE-JUMP CHECK: OK")


if __name__ == "__main__":
    main()
