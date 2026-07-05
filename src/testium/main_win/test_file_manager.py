import os
import sys
import traceback
from queue import Empty

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QProgressDialog

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from main_win.test_controller_service import TestControllerService
from main_win import file_dialog
import interpreter.utils.settings as prefs
from runtime.tum_except import ETUMFileError, ETUMRuntimeError


class TestFileManager:
    """Manages test file loading, process lifecycle, and recent files."""

    def __init__(self, win) -> None:
        self._win = win

    # --- Process lifecycle ---

    def clear_process(self):
        """Tear down the child process and every resource attached to the
        currently-loaded test so nothing leaks across a GUI reload.

        Runs unconditionally (not only when the child is alive): a crashed or
        already-dead child still holds a controller with two multiprocessing
        Queues (feeder thread + pipe fds + semaphores) that must be closed, and
        the globals table must be reset. A too-strict guard used to skip all of
        this, orphaning those resources on every subsequent reload.
        """
        w = self._win
        # Ask the child to stop/close only while it can still answer, then make
        # sure it is really gone.
        if w.test_proc is not None:
            if w.test_proc.is_alive() and w.test_service is not None:
                try:
                    w.test_service.stop()
                    w.test_service.close()
                except Exception:
                    pass
                w.test_proc.join(timeout=5)
                if w.test_proc.is_alive():
                    w.test_proc.terminate()
                    w.test_proc.join(timeout=2)
                if w.test_proc.is_alive():
                    w.test_proc.kill()
                    w.test_proc.join()
            # Release the parent-side stdout capture pipe + thread opened in
            # TestProcess.__init__ (else each reload leaks a thread + 2 fds).
            try:
                w.test_proc.close_parent_io()
            except Exception:
                pass
            del w.test_proc
            w.test_proc = None
        # Close the control queues (feeder threads + pipe fds + semaphores) so
        # they don't accumulate reload after reload.
        if w.ts_controller is not None:
            try:
                w.ts_controller.close()
            except Exception:
                pass
            del w.ts_controller
            w.ts_controller = None
        if w.test_service is not None:
            del w.test_service
            w.test_service = None
        # Reset the globals table (clears the rows and the key→row map).
        w.d_f1_win.set_service(None)
        # Drop the previously-loaded test directory from sys.path.
        self._remove_test_dir_from_path()

    def reload(self, file_name: str):
        w = self._win
        w.disconnect_signals()
        # Snapshot user-selected checkboxes and fold state so they survive a
        # reload of the same file (same logic as session-restore through prefs).
        # checkList works only if show_checkboxes is True
        previous_check_list = w.treeTests.getCheckList()
        previous_fold_list = w.treeTests.getFoldList()
        previous_count = w.treeTests.getItemCount()
        self.clear_process()
        if self.load(file_name) and \
            w.test_service is not None and \
            w.treeTests.getItemCount() == previous_count:
                if prefs.settings.show_checkboxes :
                    w.treeTests.restoreCheckList(previous_check_list, w.test_service)
                w.treeTests.restoreFoldList(previous_fold_list)

        w.reconnect_signals()

    def _remove_test_dir_from_path(self):
        """Undo the sys.path entry added by the previous load (and any stale
        duplicate of it) so the search path can't grow across reloads — the
        parent's sys.path is inherited by every spawned child process."""
        w = self._win
        test_dir = getattr(w, "_test_dir_on_path", None)
        if test_dir is not None:
            while test_dir in sys.path:
                sys.path.remove(test_dir)
            w._test_dir_on_path = None

    def _make_progress(self, w):
        progress = QProgressDialog("Starting test process…", None, 0, 0, w)
        progress.setWindowTitle("Loading")
        progress.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(320)
        progress._force_close = False
        progress.closeEvent = lambda e: e.accept() if progress._force_close else e.ignore()
        return progress

    def _close_progress(self, progress):
        progress._force_close = True
        progress.close()

    def load(self, file_name: str) -> bool:
        """Load a test file. Returns True on success, False otherwise."""
        w = self._win
        progress = None
        try:
            if not file_name:
                raise ETUMFileError("No file to load")

            file_name = os.path.abspath(file_name)
            # Kept so Refresh can retry even after a failed load.
            w._attempted_file = file_name
            initial_dir = os.path.dirname(file_name)

            if not os.path.isdir(initial_dir):
                raise ETUMFileError("Could not find %s directory" % initial_dir)
            if not os.path.isfile(file_name):
                raise ETUMFileError("Could not find %s file" % file_name)

            progress = self._make_progress(w)
            progress.show()
            QApplication.processEvents()

            w.testFile = None
            w.ts_controller = TestSetController()
            w.test_service = TestControllerService(w.ts_controller)
            w.d_f1_win.set_service(w.test_service)
            w.test_proc = TestProcess(
                file_name,
                w.status_queue,
                w.ts_controller,
                w.config_files,
                w.defines,
                self._defaults_for_process(),
            )
            w.test_proc.start()
            progress.setLabelText("Loading test file…")
            while w.test_proc.is_alive():
                try:
                    if w.test_service.loaded(timeout=0.05):
                        break
                except Empty:
                    w.test_service.clear()
                QApplication.processEvents()

            if not w.test_proc.is_alive():
                # Child died during load: release its parent-side capture
                # pipe/thread and control queues before dropping the refs,
                # otherwise a failed reload leaks a thread + fds too.
                try:
                    w.test_proc.close_parent_io()
                except Exception:
                    pass
                del w.test_proc
                w.test_proc = None
                del w.test_service
                w.test_service = None
                w.d_f1_win.set_service(None)
                try:
                    w.ts_controller.close()
                except Exception:
                    pass
                del w.ts_controller
                w.ts_controller = None
                raise ETUMRuntimeError(
                    "Test could not be loaded. See the log above for the cause "
                    "(syntax error, missing file, missing module, ...)."
                )

            progress.setLabelText("Building test tree…")
            QApplication.processEvents()
            test_data = w.test_service.tree()
            w.treeTests.clear()
            w._reset_search()
            QApplication.processEvents()
            w.treeTests.loadTestRecursively(w.treeTests.invisibleRootItem(), test_data)
            self._close_progress(progress)
            progress = None
            w.treeTests.setFoldDefault()
            w.treeTests.updateTreeSkipState(w.test_service)
            w.d_f1_win.load_initial_vars(w.test_service.get_gd_vars())

            w.checkSelect.setChecked(True)
            w.testFile = file_name
            test_dir = os.path.dirname(w.testFile)

            if test_dir not in sys.path:
                sys.path.append(test_dir)
            w._test_dir_on_path = test_dir
            w.statusBar().showMessage("Test file loaded", 10000)
            w.textLog.set_test_dir(test_dir)
            self.add_file_to_recent(file_name)
            w.setWindowTitle(w.mainWindowTitle + " - " + w.testFile)
            w.actionStart_test.setEnabled(True)
            w.actionRefresh_test.setEnabled(True)
            w.show_checkboxes()
            return True
        except:
            if progress is not None:
                self._close_progress(progress)
            w.statusBar().showMessage("No test file could be loaded", 10000)
            w.treeTests.clear()
            # Keep Refresh available to retry after fixing the file.
            w.actionStart_test.setDisabled(True)
            w.actionRefresh_test.setEnabled(True)
            print(traceback.format_exc())
            return False

    def _defaults_for_process(self) -> dict:
        d = {}
        pp = prefs.settings.python_bin
        if pp != "":
            d["python_bin"] = pp
        pp = prefs.settings.lua_bin
        if pp != "":
            d["lua_bin"] = pp
        return d

    # --- Recent files ---

    def add_file_to_recent(self, filename: str):
        files = prefs.settings.recent_files
        try:
            files.remove(filename)
        except ValueError:
            pass
        files.insert(0, filename)
        del files[self._win.MaxRecentFiles:]
        prefs.settings.recent_files = files
        for widget in QApplication.topLevelWidgets():
            from main_win.testium_win import MainWindow
            if isinstance(widget, MainWindow):
                widget.file_manager.update_recent_file_actions()

    def update_recent_file_actions(self):
        w = self._win
        files = prefs.settings.recent_files
        numRecentFiles = min(len(files), w.MaxRecentFiles)
        for i in range(numRecentFiles):
            text = "&%d %s" % (i + 1, w._stripped_name(files[i]))
            w.recentFileActs[i].setText(text)
            w.recentFileActs[i].setData(files[i])
            w.recentFileActs[i].setVisible(True)
        for j in range(numRecentFiles, w.MaxRecentFiles):
            w.recentFileActs[j].setVisible(False)
        w.separatorAct.setVisible(numRecentFiles > 0)

    def on_open_recent_file(self):
        w = self._win
        action = w.sender()
        if action:
            self.reload(action.data())

    def on_open_test(self):
        w = self._win
        d = ""
        if w.testFile is not None:
            d = os.path.dirname(w.testFile)
        file_name, _ = QFileDialog.getOpenFileName(
            w, "Open the test file", d,
            "testium file (*.tum);;All Files (*)", options=file_dialog.options()
        )
        if file_name:
            self.reload(file_name)
