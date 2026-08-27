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
    from interpreter.test_items.dialog_presenter import (
        AUTO_CLOSE_MS, accepts, arg_at, mute_frozen_streams, send_result)
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = TestDialogWindow()
    d.resize(387, 224)
    d.setMinimumSize(320, 200)
    d.setWindowFlags(Qt.WindowStaysOnTopHint)
    d.setWindowTitle(args[0])
    d.labelDialog.setText(args[1])
    d.lineEdit.setText(args[2])
    d.lineEdit.setFocus()
    auto_result = arg_at(args, 3)
    if auto_result is not None:
        auto_value = arg_at(args, 4)
        def _auto_close():
            if auto_value is not None:
                d.lineEdit.setText(auto_value)
            d.accept() if accepts(auto_result) else d.reject()
        QTimer.singleShot(AUTO_CLOSE_MS, _auto_close)
    dres = d.exec()

    if dres == QDialog.Rejected:
        success = False
    send_result(conn, d.lineEdit.text(), success)

    mute_frozen_streams()


if __name__ == '__main__':
    main(sys.argv[1:])



