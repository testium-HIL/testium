import sys

from PySide6.QtCore import (Qt)
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
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = TestDialogWindow()
    d.setFixedSize(700,600)
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

        dres = d.exec()

        if dres == QDialog.Rejected:
            success = False

    if conn is not None:
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
    main(sys.argv[1:], None)



