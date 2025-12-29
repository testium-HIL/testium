from PySide6.QtCore import (QThread)


class ThreadTestOutput(QThread):

    def __init__(self, stream, queue, parent=None):
        super().__init__(parent)
        self._stream = stream
        self._queue = queue
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        """ read the stream and print it in the log window line by line
        """

        while not self._is_stopped:
            try:
                lines=self._stream.read().splitlines()
                for line in lines:
                    if len(line) >= 1:
                        self._queue.put(line)

                QThread.msleep(100)
            except:
                QThread.msleep(100)
