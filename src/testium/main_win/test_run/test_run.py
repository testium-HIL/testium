from time import sleep
import importlib
from PySide6.QtCore import (Signal, QThread)

from gui import run_io


class ThreadTestStatus(QThread):
    statusToBeUpdated = Signal(dict)
    testSetIsFinished = Signal()
    gdUpdated = Signal(str, object)
    gdDeleted = Signal(str)

    def __init__(self, status_queue, parent=None, debug=False):
        super().__init__(parent)
        self.__to_be_stopped = False
        self._status_queue = status_queue
        self.__debug = debug

    def run(self):
        if self.__debug:
            self.debugpy = importlib.import_module("debugpy")
        stopping = False
        while True:
            while not self._status_queue.empty():
                run_io.dispatch_status(
                    self._status_queue.get(),
                    self.gdUpdated.emit,
                    self.gdDeleted.emit,
                    self.testSetIsFinished.emit,
                    self.statusToBeUpdated.emit)
            if stopping:
                break
            if self.__to_be_stopped:
                stopping = True
            sleep(0.1)

    def stop(self):
        self.__to_be_stopped = True
