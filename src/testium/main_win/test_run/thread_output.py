from PySide6.QtCore import (QThread)

from gui import run_io


class ThreadTestOutput(QThread):

    def __init__(self, stream, queue, parent=None):
        super().__init__(parent)
        self._stream = stream
        self._queue = queue
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        """Read the stream and queue it line by line for the log window."""
        while not self._is_stopped:
            try:
                run_io.pump_lines(self._stream, self._queue.put)
            except Exception:
                pass
            QThread.msleep(100)
