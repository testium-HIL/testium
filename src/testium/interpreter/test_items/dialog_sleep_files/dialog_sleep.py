import sys
import os
from PySide6.QtCore import (Qt, QTimer, QTime)
from PySide6.QtWidgets import (QApplication, QDialog)

from interpreter.test_items.dialog_sleep_files import dialog_sleep_win

class DialogSleepWindow(QDialog, dialog_sleep_win.Ui_SleepDialogWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.timeEdit.setDisplayFormat("HH:mm:ss")
        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.stop()
        self.timer.timeout.connect(self.on_timerEvent)

    def time(self, secs):
        hrs = secs//(3600)
        min = (secs - (hrs * 3600))//60
        s = secs - (hrs * 3600) - (min * 60)
        return QTime(hrs, min, s)

    def setupTimer(self, timeout):
        self.timeout = int(timeout)

        # time settings ...
        self.timeEdit.setTime(self.time(self.timeout))
        self.timer.setSingleShot(False)
        self.timer.setInterval(1000)
        self.timer.start()

    def on_timerEvent(self):
        self.timeout = self.timeout - 1
        if self.timeout <= 0:
            self.accept()
        else:
            self.timeEdit.setTime(self.time(self.timeout))

def main(args, conn=None):
    success = True
    app = QApplication(sys.argv)
    d = DialogSleepWindow()
    d.setFixedSize(379,129)
    d.setWindowFlags(Qt.WindowStaysOnTopHint)
    d.setModal(True)
    d.setWindowTitle(args[0])
    d.setupTimer(float(args[1]))

    dres = d.exec()
    if dres == QDialog.Rejected:
        success = False
    res = -1
    if success:
        res = 0

    if conn:
        conn.send(success)
        conn.close()

    if hasattr(sys, "frozen"):
        #all standard streams are replaced by dummy one to avoid cx_freeze flushing bug.
        class dummyStream:
            ''' dummyStream behaves like a stream but does nothing. '''
            def __init__(self): pass
            def write(self,data): pass
            def read(self,data): pass
            def flush(self): pass
            def close(self): pass

        # and now redirect all default streams to this dummyStream:
        sys.stdout = dummyStream()
        sys.stderr = dummyStream()
        sys.stdin = dummyStream()
        sys.__stdout__ = dummyStream()
        sys.__stderr__ = dummyStream()
        sys.__stdin__ = dummyStream()


if __name__ == '__main__':
    main(sys.argv[1:])
