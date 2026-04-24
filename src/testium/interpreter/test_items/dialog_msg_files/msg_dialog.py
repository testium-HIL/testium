import sys
from multiprocessing import freeze_support

from PySide6.QtWidgets import (QApplication, QMessageBox)
from PySide6.QtCore import Qt, QTimer


def main(args):
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    msg = QMessageBox()
    msg.setWindowFlags(Qt.WindowStaysOnTopHint)
    msg.setWindowTitle(args[0])
    msg.setText(args[1])
    msg.setIcon(QMessageBox.Information)
    msg.setStandardButtons(QMessageBox.Ok)
    if len(args) > 2:
        QTimer.singleShot(2000, lambda: msg.button(QMessageBox.Ok).click())
    msg.exec()

    if hasattr(sys, "frozen"):
        class dummyStream:
            def __init__(self): pass
            def write(self, data): pass
            def read(self, data): pass
            def flush(self): pass
            def close(self): pass

        sys.stdout = dummyStream()
        sys.stderr = dummyStream()
        sys.stdin = dummyStream()
        sys.__stdout__ = dummyStream()
        sys.__stderr__ = dummyStream()
        sys.__stdin__ = dummyStream()


if __name__ == '__main__':
    main(sys.argv[1:])
