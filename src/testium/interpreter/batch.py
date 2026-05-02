import os
import sys
import platform
import threading
from time import sleep
from signal import signal, SIGINT
from queue import Empty
from multiprocessing import Queue

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from runtime.tum_except import ETUMFileError, ETUMRuntimeError
from runtime.stdout_redirect import stdio_redir


class Batch:
    def __init__(
        self,
        test_file,
        config_files,
        defines,
        report_file,
        report_type,
        report_pattern,
        no_color,
        text_mode=False,
    ):
        try:
            try:
                file_name = os.path.abspath(test_file)
                initial_dir = os.path.dirname(file_name)

                if not os.path.isdir(initial_dir):
                    raise ETUMFileError("Could not find %s directory" % (initial_dir))
                if not os.path.isfile(file_name):
                    raise ETUMFileError("Could not find %s file" % (file_name))

                if not file_name:
                    raise ETUMFileError("No file to load")

                outstream = sys.stdout
                if "Linux" in platform.system() and not no_color:
                    try:
                        from interpreter.utils.termlog import TermLog

                        outstream = TermLog(sys.stdout)
                        stdio_redir.redirect(outstream)
                    except ModuleNotFoundError:
                        print(
                            "Colored console not supported by the system."
                            + " If you want it, please install colorama module"
                        )

                signal(SIGINT, self.sigint_handler)

                self._success = False
                msg_queue = Queue()
                self.tst_ctrl = TestSetController()
                tst_proc = TestProcess(
                    file_name,
                    msg_queue,
                    self.tst_ctrl,
                    config_files,
                    defines,
                    text_mode=text_mode,
                )
                tst_proc.start()

                # Wait for TestProcess to finish loading.
                # Run the blocking control("loaded") in a daemon thread so we
                # can watch for unexpected process death in the main thread.
                _loaded_event = threading.Event()
                def _wait_loaded():
                    self.tst_ctrl.control("loaded")
                    _loaded_event.set()
                threading.Thread(target=_wait_loaded, daemon=True).start()
                while not _loaded_event.wait(timeout=0.1):
                    if not tst_proc.is_alive():
                        raise ETUMRuntimeError("TestProcess terminated unexpectedly during load")

                self.tst_ctrl.control(
                    "report",
                    rep_path=report_file,
                    rep_type=report_type,
                    pattern=report_pattern,
                )
                # Start test execution
                self.tst_ctrl.control("execute")

                # Wait for the "finished" signal
                while True:
                    try:
                        m = msg_queue.get(timeout=0.2)
                        if "id" in m and m["id"] is None:
                            # id key present and None -> finished
                            self._success = m.get("success", False)
                            break
                    except Empty:
                        if not tst_proc.is_alive():
                            break
                        continue

                # Close the process and wait for termination
                if tst_proc.is_alive():
                    self.tst_ctrl.control("close")
                tst_proc.join()

            except Exception as e:
                print("Exception encountered:")
                print(str(e))
        finally:
            stdio_redir.restore()

    @property
    def success(self):
        return self._success

    def sigint_handler(self, signal_received, frame):
        try:
            self.tst_ctrl.control("stop", timeout=5)
        except Exception:
            pass
