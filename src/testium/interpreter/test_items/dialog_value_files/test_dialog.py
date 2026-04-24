import sys
import os

from PySide6.QtWidgets import (QApplication, QDialog)
from PySide6.QtCore import Qt, QTimer

from interpreter.test_items.dialog_value_files import dialog_value_win
from multiprocessing import  freeze_support

class TestDialogWindow(QDialog, dialog_value_win.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


def main(args, conn=None):
    success = True
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = TestDialogWindow()
    d.setFixedSize(387,224)
    d.setWindowFlags(Qt.WindowStaysOnTopHint)
    d.setWindowTitle(args[0])
    d.labelDialog.setText(args[1])
    d.lineEdit.setText(args[2])
    d.lineEdit.setFocus()
    auto_result = args[3] if len(args) > 3 else None
    if auto_result is not None:
        auto_value = args[4] if len(args) > 4 else None
        def _auto_close():
            if auto_value is not None:
                d.lineEdit.setText(auto_value)
            d.accept() if auto_result.lower() == 'ok' else d.reject()
        QTimer.singleShot(2000, _auto_close)
    dres = d.exec()

    if dres == QDialog.Rejected:
        success = False
    if conn:
        conn.send([d.lineEdit.text(), success])
        conn.close()
    else:
        print(d.lineEdit.text(), end='')

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



