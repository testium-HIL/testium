from PySide6.QtCore import QObject, Signal

from gui import run_io


class OutLog(QObject):
    logToBeAppended = Signal(str)

    def __init__(self, out=None):
        super().__init__(None)
        self._tee = run_io.LogTee(self.logToBeAppended.emit, out)

    def set(self, file_handle):
        self._tee.set(file_handle)

    def reset(self):
        self._tee.reset()

    def write(self, m):
        self._tee.write(m)

    def writeln(self, m=""):
        self._tee.writeln(m)

    def flush(self):
        self._tee.flush()
