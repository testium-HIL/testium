import sys
from multiprocessing import freeze_support

from PySide6.QtWidgets import (QApplication, QMessageBox)
from PySide6.QtCore import Qt, QTimer


def main(args, conn):
    try:
        from interpreter.test_items.dialog_presenter import (
            AUTO_CLOSE_MS, accepts, mute_frozen_streams)
        from interpreter.test_items import dialog_env
        dialog_env.setup()
        app = QApplication(['testium'])
        msg = QMessageBox()
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg.setWindowTitle(args[0])
        msg.setText(args[1])
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        auto_result = args[2] if len(args) > 2 else None
        if auto_result is not None:
            btn = QMessageBox.Yes if accepts(auto_result) else QMessageBox.No
            QTimer.singleShot(AUTO_CLOSE_MS, lambda: msg.button(btn).click())
        reply = msg.exec()
        conn.send(reply)
    except Exception as e:
        print(f"dialog_question error: {e}", file=sys.stderr)
    finally:
        conn.close()

    mute_frozen_streams()
