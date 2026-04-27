from time import sleep
import importlib
from PySide6.QtCore import (Signal, QThread)


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
        try:
            while True:
                while not self._status_queue.empty():
                    m = self._status_queue.get()
                    msg_type = m.get("type")
                    if msg_type == "gd_update":
                        self.gdUpdated.emit(m["key"], m["value"])
                    elif msg_type == "gd_delete":
                        self.gdDeleted.emit(m["key"])
                    elif "id" in m and m["id"] is None:
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
