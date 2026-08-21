import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QDialog)
from PySide6 import (QtGui)

try:
    from interpreter.test_items.dialog_image_files import dialog_image_win
except:
    import dialog_image_win
from multiprocessing import  freeze_support

class TestDialogWindow(QDialog, dialog_image_win.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

def main(args, conn):
    success = True
    from interpreter.test_items.dialog_presenter import (
        AUTO_CLOSE_MS, accepts, mute_frozen_streams)
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = TestDialogWindow()
    d.resize(700, 600)
    d.setMinimumSize(400, 300)
    d.setWindowFlags(Qt.WindowStaysOnTopHint)
    d.setWindowTitle(args[0])
    d.labelDialog.setText(args[1])

    image = QtGui.QImage(args[2])

    if image.isNull():
        print('Image %s could not be loaded...' % (args[2]))
        success = False

    else:
        image2 = image.scaled(d.labelImage.width(), d.labelImage.height(),
                     aspectMode=Qt.KeepAspectRatio)

        d.labelImage.setPixmap(QtGui.QPixmap.fromImage(image2))

        auto_result = args[3] if len(args) > 3 else None
        if auto_result is not None:
            QTimer.singleShot(AUTO_CLOSE_MS,
                              lambda: d.accept() if accepts(auto_result)
                              else d.reject())

        dres = d.exec()

        if dres == QDialog.Rejected:
            success = False

    if conn is not None:
        conn.send(success)
        conn.close()

    mute_frozen_streams()


if __name__ == '__main__':
    main(sys.argv[1:], None)



