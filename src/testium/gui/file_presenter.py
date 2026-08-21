# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Test-file presenter: loads/reloads the test child process, owns the
process triad (process, controller, service) and the recent-files list.
Pure Python; the toolkit side implements FileView."""

import os
import sys
import traceback
import weakref
from queue import Empty

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from gui.test_controller_service import TestControllerService
import interpreter.utils.settings as prefs
from runtime.tum_except import ETUMFileError, ETUMRuntimeError

# Every live presenter, so a recent-files change made in one window
# refreshes the menu of the others.
_presenters = weakref.WeakSet()


class FilePresenter:
    def __init__(self, view, status_queue, config_files, defines,
                 max_recent=10) -> None:
        self._view = view
        self._status_queue = status_queue
        self._config_files = config_files
        self._defines = defines
        self._max_recent = max_recent
        self.test_proc = None
        self.ts_controller = None
        self.test_service = None
        self.test_file = None
        self.attempted_file = None
        self._test_dir_on_path = None
        _presenters.add(self)

    # --- Process lifecycle ---

    def clear_process(self):
        """Tear down the child process and every resource attached to the
        currently-loaded test so nothing leaks across a reload.

        Runs unconditionally (not only when the child is alive): a crashed
        or already-dead child still holds a controller with two
        multiprocessing Queues (feeder thread + pipe fds + semaphores) that
        must be closed, and the globals table must be reset."""
        if self.test_proc is not None:
            if self.test_proc.is_alive() and self.test_service is not None:
                try:
                    self.test_service.stop()
                    self.test_service.close()
                except Exception:
                    pass
                self.test_proc.join(timeout=5)
                if self.test_proc.is_alive():
                    self.test_proc.terminate()
                    self.test_proc.join(timeout=2)
                if self.test_proc.is_alive():
                    self.test_proc.kill()
                    self.test_proc.join()
            # Release the parent-side stdout capture pipe + thread opened in
            # TestProcess.__init__ (else each reload leaks a thread + 2 fds).
            try:
                self.test_proc.close_parent_io()
            except Exception:
                pass
            self.test_proc = None
        # Close the control queues (feeder threads + pipe fds + semaphores)
        # so they don't accumulate reload after reload.
        if self.ts_controller is not None:
            try:
                self.ts_controller.close()
            except Exception:
                pass
            self.ts_controller = None
        self.test_service = None
        # Reset the globals table (clears the rows and the key→row map).
        self._view.set_variables_service(None)
        # Drop the previously-loaded test directory from sys.path.
        self._remove_test_dir_from_path()

    def reload(self, file_name: str):
        self._view.begin_tree_swap()
        # Snapshot fold/check/breakpoint states keyed by item path so they
        # survive a reload of the same file even when items were added or
        # removed. Taken before clear_process/load (load resets test_file).
        previous_states = self._view.snapshot_tree_states()
        previous_file = self.test_file
        if previous_file:
            self._view.stash_file_state(previous_file)
        self.clear_process()
        if self.load(file_name) and self.test_service is not None:
            if previous_states and previous_file and \
                    os.path.normcase(self.test_file) \
                    == os.path.normcase(previous_file):
                self._view.restore_tree_states(previous_states)
            else:
                self._view.restore_file_state()

        self._view.end_tree_swap()

    def _remove_test_dir_from_path(self):
        """Undo the sys.path entry added by the previous load (and any
        stale duplicate of it) so the search path can't grow across
        reloads — the parent's sys.path is inherited by every spawned
        child process."""
        if self._test_dir_on_path is not None:
            while self._test_dir_on_path in sys.path:
                sys.path.remove(self._test_dir_on_path)
            self._test_dir_on_path = None

    def load(self, file_name: str) -> bool:
        """Load a test file. Returns True on success, False otherwise."""
        in_progress = False
        try:
            if not file_name:
                raise ETUMFileError(
                    "No file to load. Internal error, please report it.")

            file_name = os.path.abspath(file_name)
            # Kept so Refresh can retry even after a failed load.
            self.attempted_file = file_name
            initial_dir = os.path.dirname(file_name)

            if not os.path.isdir(initial_dir):
                raise ETUMFileError(
                    "Could not find %s directory" % initial_dir)
            if not os.path.isfile(file_name):
                raise ETUMFileError("Could not find %s file" % file_name)

            self._view.begin_load()
            in_progress = True
            self._view.pump()

            self.test_file = None
            self.ts_controller = TestSetController()
            self.test_service = TestControllerService(self.ts_controller)
            self._view.set_variables_service(self.test_service)
            self.test_proc = TestProcess(
                file_name,
                self._status_queue,
                self.ts_controller,
                self._config_files,
                self._defines,
                self._defaults_for_process(),
            )
            self.test_proc.start()
            self._view.set_load_phase("Loading test file…")
            while self.test_proc.is_alive():
                try:
                    if self.test_service.loaded(timeout=0.05):
                        break
                except Empty:
                    self.test_service.clear()
                self._view.pump()

            if not self.test_proc.is_alive():
                # Child died during load: release its parent-side capture
                # pipe/thread and control queues before dropping the refs,
                # otherwise a failed reload leaks a thread + fds too.
                try:
                    self.test_proc.close_parent_io()
                except Exception:
                    pass
                self.test_proc = None
                self.test_service = None
                self._view.set_variables_service(None)
                try:
                    self.ts_controller.close()
                except Exception:
                    pass
                self.ts_controller = None
                raise ETUMRuntimeError(
                    f"{file_name} could not be loaded. See the log above "
                    "for the cause (syntax error, missing file, missing "
                    "module, ...)."
                )

            self._view.set_load_phase("Building test tree…")
            self._view.pump()
            test_data = self.test_service.tree()
            gd_vars = self.test_service.get_gd_vars()
            self._view.end_load()
            in_progress = False

            self.test_file = file_name
            test_dir = os.path.dirname(file_name)
            if test_dir not in sys.path:
                sys.path.append(test_dir)
            self._test_dir_on_path = test_dir

            self._view.show_loaded_test(test_data, gd_vars, test_dir)
            self.add_file_to_recent(file_name)
            self._view.set_window_file(file_name)
            return True
        except:
            if in_progress:
                self._view.end_load()
            self._view.show_load_failure()
            print(f"{file_name or 'The test file'} could not be loaded: "
                  "unexpected error, traceback follows.")
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
        # Set only when true, so config files and -d keep priority.
        if prefs.settings.debug_output:
            d["test_debug"] = True
        return d

    # --- Recent files ---

    def add_file_to_recent(self, filename: str):
        files = prefs.settings.recent_files
        try:
            files.remove(filename)
        except ValueError:
            pass
        files.insert(0, filename)
        del files[self._max_recent:]
        prefs.settings.recent_files = files
        for presenter in list(_presenters):
            presenter.update_recent_file_actions()

    def update_recent_file_actions(self):
        self._view.update_recent_files(prefs.settings.recent_files)
