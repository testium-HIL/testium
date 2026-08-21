import sys
from multiprocessing import freeze_support

from PySide6.QtWidgets import (QApplication, QMessageBox)
from PySide6.QtCore import Qt, QTimer


def main(args):
    from interpreter.test_items.dialog_presenter import (
        AUTO_CLOSE_MS, accepts, mute_frozen_streams)
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
        QTimer.singleShot(AUTO_CLOSE_MS,
                          lambda: msg.button(QMessageBox.Ok).click())
    msg.exec()

    mute_frozen_streams()


if __name__ == '__main__':
    main(sys.argv[1:])
