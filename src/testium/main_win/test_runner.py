import os
import traceback
from enum import Enum, auto
from tempfile import NamedTemporaryFile

from PySide6 import QtGui
from PySide6.QtCore import QDateTime
from PySide6.QtGui import QIcon, QPixmap

from interpreter.utils.icons import icon_prefix
import interpreter.utils.settings as prefs


class TestState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()


class TestRunner:
    """Manages the test execution lifecycle: start/pause/stop, timers, log file, UI adaptation."""

    def __init__(self, win) -> None:
        self._win = win
        self.logFileHandler = None
        self.state = TestState.IDLE

    # --- Timer helpers ---

    def start_pause_timer(self):
        w = self._win
        w.timerPause.setSingleShot(False)
        w.timerPause.setInterval(500)
        w.timerPause.start()
        w.timerPause.state = False

    # --- Execution control ---

    def on_start_test(self):
        w = self._win

        if self.state != TestState.IDLE:
            if self.state == TestState.RUNNING:
                w.test_service.pause()
                self.start_pause_timer()
                self.state = TestState.PAUSED
                self._set_step_actions_enabled(True)
            else:
                w.test_service.cont()
                w.timerPause.stop()
                w.timerPause.state = False
                self.on_timer_pause()
                self.state = TestState.RUNNING
                self._set_step_actions_enabled(False)
            return

        self._start_run()

    def _start_run(self):
        w = self._win
        w.start_time = QDateTime.currentDateTime()

        # Log file setup
        log_file = w.editLogFilePath.text()
        if w.buttLogFileSaved.isChecked() and (log_file != ""):
            try:
                if not os.path.isabs(log_file):
                    default_path = prefs.settings.log_path
                    default_path = w.test_service.process_param(default_path)
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
                self.logFileHandler = open(log_file, "w")
                w.out_log.set(self.logFileHandler)
                w.logFileName = log_file
            except:
                self.logFileHandler = NamedTemporaryFile(mode="w", suffix=".log", delete=False)
                w.out_log.set(self.logFileHandler)
                w.logFileName = self.logFileHandler.name
        else:
            self.logFileHandler = NamedTemporaryFile(mode="w", suffix=".log", delete=False)
            w.out_log.set(self.logFileHandler)
            w.logFileName = self.logFileHandler.name

        # Report setup and execution
        rep_file = w.test_service.process_param(w.reportFileName)
        w.test_service.set_report(rep_file, w.report_type, w.report_pattern)
        self.adapt_interface_during_test()
        w.treeTests.clearAllStatus()
        try:
            w.textLog.clear()
            w.textLog.appendPlainText("Test is started\n")
            w.timer.setSingleShot(False)
            w.timer.setInterval(100)
            w.timer.start()
            w.test_service.set_test_outputs([w.logFileName])
            w.test_service.execute()
        except:
            print(traceback.format_exc())
            self.restore_interface_after_test()

    def on_stop_test(self):
        self._win.test_service.stop()

    def on_step_over(self):
        if self.state == TestState.PAUSED:
            # State stays PAUSED: execution resumes and pauses again on the
            # next item; the tree highlight follows the 'started' statuses.
            self._win.test_service.step_over()

    def on_step_out(self):
        if self.state == TestState.PAUSED:
            self._win.test_service.step_out()

    def on_step_into(self):
        if self.state == TestState.PAUSED:
            self._win.test_service.step_into()
        elif self.state == TestState.IDLE and self._win.actionStart_test.isEnabled():
            # Arm the step before 'execute' (ordered on the command queue):
            # the run starts paused on its first item.
            self._win.test_service.step_into()
            self._start_run()
            if self.state == TestState.RUNNING:  # _start_run may have failed
                self.state = TestState.PAUSED
                self.start_pause_timer()
                self._set_step_actions_enabled(True)

    def _set_step_actions_enabled(self, enabled):
        w = self._win
        w.actionStep_over.setEnabled(enabled)
        w.actionStep_into.setEnabled(enabled)
        w.actionStep_out.setEnabled(enabled)

    def on_run_finished(self):
        w = self._win
        w.timer.setSingleShot(True)
        w.timer.setInterval(1000)
        txt = w.stream.read()
        w.textLog.appendPlainText(txt)
        w.treeTests.clearHighlights()
        self.restore_interface_after_test()

        if self.logFileHandler is not None:
            w.out_log.reset()
            self.logFileHandler.write(txt + "\n")
            self.logFileHandler.close()
        self.logFileHandler = None

        w.textLog.appendPlainText("Test is finished")
        w.run_exit_code = 0 if w.treeTests.getGlobalSuccess() else 1
        if w.runandclose:
            w.on_actionExit_triggered()

    def on_breakpoint(self):
        self.state = TestState.PAUSED
        self.start_pause_timer()
        self._set_step_actions_enabled(True)

    # --- Timer slots ---

    def on_timer_event(self):
        w = self._win
        text_to_append = []
        while not w.threads_queue.empty():
            text_to_append.append(w.threads_queue.get())
        if text_to_append:
            for t in text_to_append:
                w.textLog.appendPlainText(t)
                if self.logFileHandler is not None:
                    self.logFileHandler.write(t + "\n")
                    self.logFileHandler.flush()

    def on_timer_blink(self):
        w = self._win
        if w.buttBlink.current_color != "gray":
            self.set_blink_gray()
        elif w.treeTests.getGlobalSuccess():
            self.set_blink_green()
        else:
            self.set_blink_red()

    def on_timer_pause(self):
        w = self._win
        if self.state == TestState.PAUSED:
            icon = QtGui.QIcon()
            if w.timerPause.state:
                icon.addPixmap(QtGui.QPixmap(icon_prefix() + "/pause2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            else:
                icon.addPixmap(QtGui.QPixmap(icon_prefix() + "/pause.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            w.timerPause.state = not w.timerPause.state
            w.actionStart_test.setIcon(icon)

    def on_timer_count(self):
        w = self._win
        secfromstart = w.start_time.secsTo(QDateTime.currentDateTime())
        w.label_runtime.setText(
            "%02d:%02d:%02d" % (secfromstart / 3600, (secfromstart / 60) % 60, secfromstart % 60)
        )

    # --- Interface adaptation ---

    def adapt_interface_during_test(self):
        w = self._win
        try:
            w.disconnect_signals()
            w.actionOpenTest.setDisabled(True)
            w.actionExit.setDisabled(True)
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_prefix() + "/pause2.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
            w.actionStart_test.setIcon(icon)
            w.actionStart_test.setText("Pause test")
            w.actionPreferences.setDisabled(True)
            w.actionRefresh_test.setDisabled(True)
            # Show Results stays available during the run (log grows live).
            w.actionShow_Results.setEnabled(True)
            w.actionSave_report.setDisabled(True)
            w.logSettingsBox.setDisabled(True)
            w.actionStop_test.setEnabled(True)
            self._set_step_actions_enabled(False)
            if prefs.settings.show_checkboxes:
                w._checklist = w.treeTests.getCheckList()
                w.treeTests.removeCheckBoxes()
            w.checkSelect.setDisabled(True)
            w.checkFold.setDisabled(True)
            w.timerBlink.setSingleShot(False)
            w.timerBlink.setInterval(1000)
            w.timerBlink.start()
            self.set_blink_green()
            w.treeTests.clearGlobalSuccess()
        finally:
            self.state = TestState.RUNNING

    def restore_interface_after_test(self):
        w = self._win
        try:
            w.timerPause.stop()
            w.timerBlink.stop()
            w.actionOpenTest.setEnabled(True)
            w.actionExit.setEnabled(True)
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_prefix() + "/start.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            w.actionStart_test.setIcon(icon)
            w.actionStart_test.setText("Start test")
            w.actionPreferences.setEnabled(True)
            w.actionRefresh_test.setEnabled(True)
            w.actionStop_test.setDisabled(True)
            self._set_step_actions_enabled(False)
            w.actionStep_into.setEnabled(w.actionStart_test.isEnabled())
            w.actionShow_Results.setEnabled(True)
            w.actionSave_report.setEnabled(True)
            w.logSettingsBox.setEnabled(True)
            if prefs.settings.show_checkboxes:
                w.checkSelect.setEnabled(True)
                w.treeTests.showCheckBoxes(w._checklist, w.test_service)
            w.checkFold.setEnabled(True)
            w.treeTests.setChildrenEnabled()
            w.reconnect_signals()
            if w.treeTests.getGlobalSuccess():
                self.set_blink_green()
            else:
                self.set_blink_red()
        finally:
            self.state = TestState.IDLE

    # --- Blink indicator ---

    def set_blink_green(self):
        w = self._win
        w.buttBlink.setIcon(w.iconBlinkGreen)
        w.buttBlink.current_color = "green"

    def set_blink_red(self):
        w = self._win
        w.buttBlink.setIcon(w.iconBlinkRed)
        w.buttBlink.current_color = "red"

    def set_blink_gray(self):
        w = self._win
        w.buttBlink.setIcon(w.iconBlinkGray)
        w.buttBlink.current_color = "gray"
