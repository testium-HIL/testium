from time import sleep
import importlib
from PySide6.QtCore import (Signal, QThread)

# class ThreadTestRun(QThread):

#     def __init__(
#         self,
#         test_proc: TestProcess,
#         status_thread,
#         tst_ctrl: TestSetController,
#         debug=False,
#     ):
#         super().__init__(None)
#         self._test_proc = test_proc
#         self._tst_ctrl = tst_ctrl
#         self._debug = debug
#         self._status_thread = status_thread
#         if debug:
#             self.debugpy = importlib.import_module("debugpy")

#     def run(self):
#         if self._debug:
#             self.debugpy.debug_this_thread()

#         # start tests
#         try:
#             self._test_set.execute()
#         except:
#             print(traceback.format_exc())
#             # raise
#         self._status_thread.stop()
#         if self._status_thread.isRunning():
#             self._status_thread.wait()

#     def stop(self):
#         if self.isRunning():
#             self._tst_ctrl.control("stop")


class ThreadTestStatus(QThread):
    statusToBeUpdated = Signal(dict)
    testSetIsFinished = Signal()

    def __init__(self, status_queue, parent=None, debug=False):
        super().__init__(parent)
        self.__to_be_stopped = False
        self._status_queue = status_queue
        self.__debug = debug

    def run(self):
        if self.__debug:
            self.debugpy = importlib.import_module("debugpy")
        stopping = False
        try:
            while True:
                while not self._status_queue.empty():
                    m = self._status_queue.get()
                    if m.get("id", None) is None:
                        self.testSetIsFinished.emit()
                    else:
                        self.statusToBeUpdated.emit(m)
                if stopping:
                    break
                if self.__to_be_stopped:
                    stopping = True
                sleep(0.1)

        finally:
            pass
            #self.testSetIsFinished.emit()

    def stop(self):
        self.__to_be_stopped = True
