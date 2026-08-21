#!/usr/bin/env python3
"""Source-mode check of the run presenter, without any toolkit.

Drives gui/run_presenter.py with fake view/scheduler/service: state
machine, run log opening and rotation, pause icon flip, exit code and
the run-and-close path. No PySide6 import anywhere in the chain. Run by
run.sh in source mode.
"""
import os
import queue
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

WORK = tempfile.mkdtemp(prefix="testium-presenter-")
os.environ["HOME"] = WORK
os.makedirs(os.path.join(WORK, ".config"))
import platform
if "windows" in platform.system().lower():
    os.environ["APPDATA"] = WORK

import interpreter.utils.settings as prefs
prefs.init()

from gui.run_presenter import RunPresenter, TestState


def fail(msg):
    print(f"GUI PRESENTER CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


class FakeView:
    def __init__(self, log_path):
        self._log_path = log_path
        self.ui_states = []
        self.log_lines = []
        self.lights = []
        self.start_actions = []
        self.elapsed = []
        self.messages = []
        self.log_file_name = None
        self.sink = None
        self.closed = False
        self.succeeded = True

    def apply_run_ui(self, state):
        self.ui_states.append(state)

    def set_start_action(self, text, icon):
        self.start_actions.append((text, icon))

    def set_status_light(self, color):
        self.lights.append(color)

    def set_elapsed(self, text):
        self.elapsed.append(text)

    def append_log(self, text):
        self.log_lines.append(text)

    def clear_log(self):
        self.log_lines.clear()

    def show_transient_message(self, text):
        self.messages.append(text)

    def can_start(self):
        return True

    def test_file(self):
        return "/tmp/fake.tum"

    def log_config(self):
        return (self._log_path, bool(self._log_path))

    def set_log_file_name(self, path):
        self.log_file_name = path

    def report_config(self):
        return ("", "", [])

    def attach_log_sink(self, handle):
        self.sink = handle

    def detach_log_sink(self):
        self.sink = None

    def read_captured(self):
        return ""

    def reset_run_marks(self):
        pass

    def clear_current_marks(self):
        pass

    def run_succeeded(self):
        return self.succeeded

    def close_window(self):
        self.closed = True


class FakeScheduler:
    def __init__(self):
        self.timers = {}

    def every(self, name, interval_ms, tick):
        self.timers[name] = tick

    def once(self, name, delay_ms, fire):
        self.timers[name] = fire

    def cancel(self, name):
        self.timers.pop(name, None)

    def tick(self, name):
        self.timers[name]()


class FakeService:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*a, **k):
            self.calls.append((name,) + a)
            return a[0] if a else None
        return call


def main():
    log_path = os.path.join(WORK, "logs", "run.log")
    view = FakeView(log_path)
    sched = FakeScheduler()
    service = FakeService()
    q = queue.Queue()
    rp = RunPresenter(view, sched, lambda: service, q)

    if rp.state is not TestState.IDLE:
        fail("initial state not IDLE")

    # Start: RUNNING, log file created, execute sent.
    rp.on_start_test()
    if rp.state is not TestState.RUNNING:
        fail("start did not enter RUNNING")
    if view.log_file_name != log_path or not os.path.isfile(log_path):
        fail(f"log file not opened at {log_path!r} "
             f"(got {view.log_file_name!r})")
    if ("execute",) not in service.calls:
        fail(f"execute not sent: {service.calls}")

    # Output queue drained into the view and the log file.
    q.put("hello")
    sched.tick("run_poll")
    if "hello" not in view.log_lines:
        fail("output line did not reach the view")

    # Pause / resume.
    rp.on_start_test()
    if rp.state is not TestState.PAUSED or ("pause",) not in service.calls:
        fail("pause did not work")
    if not view.ui_states or view.ui_states[-1].steps_enabled is not True:
        fail("steps not enabled while paused")
    sched.tick("pause_flip")
    if view.start_actions[-1][1] not in ("pause", "pause2"):
        fail(f"pause flip icon: {view.start_actions[-1]}")
    rp.on_start_test()
    if rp.state is not TestState.RUNNING or ("cont",) not in service.calls:
        fail("resume did not work")

    # Finish, failed verdict: exit code 1, back to IDLE.
    view.succeeded = False
    rp.on_run_finished()
    if rp.state is not TestState.IDLE:
        fail("finish did not return to IDLE")
    if rp.run_exit_code != 1:
        fail(f"exit code {rp.run_exit_code}, expected 1")
    if os.path.isfile(log_path + "-1.saved") or view.sink is not None:
        fail("log sink not detached cleanly")

    # Second run rotates the first log to -1.saved.
    view.succeeded = True
    rp.on_start_test()
    if not os.path.isfile(log_path + "-1.saved"):
        fail("previous log was not rotated to -1.saved")
    rp.on_run_finished()
    if rp.run_exit_code != 0:
        fail(f"exit code {rp.run_exit_code}, expected 0")

    # step_into from IDLE arms the step then starts, ending PAUSED.
    service.calls.clear()
    rp.on_step_into()
    if rp.state is not TestState.PAUSED:
        fail("step_into from idle did not end PAUSED")
    if service.calls[0] != ("step_into",):
        fail(f"step not armed first: {service.calls[:2]}")

    # run-and-close.
    rp.runandclose = True
    rp.on_run_finished()
    if not view.closed:
        fail("runandclose did not close the window")

    # PySide must never have been imported by this chain.
    if any(m.startswith("PySide") for m in sys.modules):
        fail("a PySide module was imported by the presenter chain")

    print("GUI PRESENTER CHECK: PASS")


if __name__ == "__main__":
    main()
