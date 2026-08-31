# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Run lifecycle presenter: start/pause/stop/step, run log file, timers,
interface state. Pure Python; the toolkit side implements RunView."""

import os
import time
import traceback
from enum import Enum, auto
from tempfile import NamedTemporaryFile

import interpreter.utils.settings as prefs
import api.testium as tm
from runtime.tum_except import ETUMRuntimeError

from gui.protocols import RunUiState


class TestState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()


class RunPresenter:
    def __init__(self, view, scheduler, service, output_queue) -> None:
        """service: zero-argument callable returning the current
        TestControllerService (None when no test is loaded)."""
        self._view = view
        self._scheduler = scheduler
        self._service = service
        self._output_queue = output_queue
        self.logFileHandler = None
        self.state = TestState.IDLE
        self.run_exit_code = -1  # -1 = test not yet completed
        self.runandclose = False
        self._t0 = None
        self._blink_gray = False
        self._pause_flip = False

    # --- Execution control ---

    def on_start_test(self):
        if self.state != TestState.IDLE:
            if self.state == TestState.RUNNING:
                self._service().pause()
                self._start_pause_flip()
                self.state = TestState.PAUSED
                self._push_ui()
            else:
                self._service().cont()
                self._stop_pause_flip()
                self.state = TestState.RUNNING
                self._push_ui()
            return

        self._start_run()

    def _start_run(self):
        service = self._service()
        self._t0 = time.monotonic()

        # Log file setup
        log_file, save_to_file = self._view.log_config()
        if save_to_file and (log_file != ""):
            try:
                if not os.path.isabs(log_file):
                    default_path = prefs.settings.log_path
                    default_path = service.process_param(default_path)
                    log_file = os.path.join(default_path, log_file)
                if not os.path.exists(os.path.dirname(log_file)):
                    os.makedirs(os.path.dirname(log_file))
                if os.path.isfile(log_file):
                    i = 0
                    fname = log_file
                    while os.path.isfile(fname):
                        i += 1
                        fname = log_file + "-" + str(i) + ".saved"
                    os.rename(log_file, fname)
                # utf-8: the locale codec (cp1252) cannot encode all log chars
                self.logFileHandler = open(log_file, "w",
                                           encoding="utf-8", errors="replace")
                chosen_name = log_file
            except BaseException as e:
                self.logFileHandler = NamedTemporaryFile(
                    mode="w", suffix=".log", delete=False,
                    encoding="utf-8", errors="replace")
                chosen_name = self.logFileHandler.name
                tm.print_warn(
                    f"Could not open the log file {log_file} ({e}); "
                    f"logging to {chosen_name} instead.")
        else:
            self.logFileHandler = NamedTemporaryFile(
                mode="w", suffix=".log", delete=False,
                encoding="utf-8", errors="replace")
            chosen_name = self.logFileHandler.name
        self._view.attach_log_sink(self.logFileHandler)
        self._view.set_log_file_name(chosen_name)

        # Report setup and execution
        rep_file_name, rep_type, rep_pattern = self._view.report_config()
        rep_file = service.process_param(rep_file_name)
        service.set_report(rep_file, rep_type, rep_pattern)
        self._enter_running()
        self._view.reset_run_marks()
        try:
            self._view.clear_log()
            self._view.append_log("Test is started\n")
            self._scheduler.every("run_poll", 100, self.on_timer_event)
            service.set_test_outputs([chosen_name])
            service.execute()
        except:
            print(f"The test run could not be started "
                  f"({self._view.test_file()}).")
            print(traceback.format_exc())
            self._leave_running()

    def on_stop_test(self):
        self._service().stop()

    def on_step_over(self):
        if self.state == TestState.PAUSED:
            # State stays PAUSED: execution resumes and pauses again on the
            # next item; the tree highlight follows the 'started' statuses.
            self._service().step_over()

    def on_step_out(self):
        if self.state == TestState.PAUSED:
            self._service().step_out()

    def on_step_into(self):
        if self.state == TestState.PAUSED:
            self._service().step_into()
        elif self.state == TestState.IDLE and self._view.can_start():
            # Arm the step before 'execute' (ordered on the command queue):
            # the run starts paused on its first item.
            self._service().step_into()
            self._start_run()
            if self.state == TestState.RUNNING:  # _start_run may have failed
                self.state = TestState.PAUSED
                self._start_pause_flip()
                self._push_ui()

    def on_rerun_step(self):
        if self.state != TestState.PAUSED:
            return
        try:
            self._service().jump_back()
        except ETUMRuntimeError as e:
            self._view.show_transient_message(str(e))

    def on_run_finished(self):
        self._scheduler.cancel("run_poll")
        self._scheduler.once("run_poll", 1000, self.on_timer_event)
        txt = self._view.read_captured()
        self._view.append_log(txt)
        self._view.clear_current_marks()
        self._leave_running()

        if self.logFileHandler is not None:
            self._view.detach_log_sink()
            self.logFileHandler.write(txt + "\n")
            self.logFileHandler.close()
        self.logFileHandler = None

        self._view.append_log("Test is finished\n")
        self.run_exit_code = 0 if self._view.run_succeeded() else 1
        if self.runandclose:
            self._view.close_window()

    def on_paused(self):
        # Engine reports an item paused (breakpoint, step, pause request,
        # jump arrival). Idempotent when already PAUSED.
        self.state = TestState.PAUSED
        self._start_pause_flip()
        self._push_ui()

    # --- Timer ticks ---

    def on_timer_event(self):
        text_to_append = []
        while not self._output_queue.empty():
            text_to_append.append(self._output_queue.get())
        for t in text_to_append:
            self._view.append_log(t)
            if self.logFileHandler is not None:
                self.logFileHandler.write(t + "\n")
                self.logFileHandler.flush()

    def _on_blink_tick(self):
        if not self._blink_gray:
            self.set_blink_gray()
        elif self._view.run_succeeded():
            self.set_blink_green()
        else:
            self.set_blink_red()
        self._on_count_tick()

    def _on_count_tick(self):
        if self._t0 is None:
            return
        sec = int(time.monotonic() - self._t0)
        self._view.set_elapsed(
            "%02d:%02d:%02d" % (sec / 3600, (sec / 60) % 60, sec % 60))

    def _on_pause_tick(self):
        if self.state == TestState.PAUSED:
            self._view.set_start_action(
                None, "pause2" if self._pause_flip else "pause")
            self._pause_flip = not self._pause_flip

    def _start_pause_flip(self):
        self._pause_flip = False
        self._scheduler.every("pause_flip", 500, self._on_pause_tick)

    def _stop_pause_flip(self):
        self._scheduler.cancel("pause_flip")
        self._pause_flip = False
        self._view.set_start_action(None, "pause")

    # --- Interface state ---

    def _push_ui(self):
        self._view.apply_run_ui(RunUiState(
            running=self.state != TestState.IDLE,
            steps_enabled=self.state == TestState.PAUSED))

    def _enter_running(self):
        try:
            self._view.set_start_action("Pause test", "pause2")
            self._scheduler.every("blink", 1000, self._on_blink_tick)
            self.set_blink_green()
        finally:
            self.state = TestState.RUNNING
            self._push_ui()

    def _leave_running(self):
        try:
            self._scheduler.cancel("pause_flip")
            self._scheduler.cancel("blink")
            self._view.set_start_action("Start test", "start")
            if self._view.run_succeeded():
                self.set_blink_green()
            else:
                self.set_blink_red()
        finally:
            self.state = TestState.IDLE
            self._push_ui()

    # --- Status light ---

    def set_blink_green(self):
        self._view.set_status_light("green")
        self._blink_gray = False

    def set_blink_red(self):
        self._view.set_status_light("red")
        self._blink_gray = False

    def set_blink_gray(self):
        self._view.set_status_light("gray")
        self._blink_gray = True
