import sys
import os

from PySide6.QtWidgets import (QApplication, QDialog)
from PySide6.QtCore import (Qt)
from PySide6.QtWidgets import QMessageBox
from multiprocessing import  freeze_support

def main(args, conn):
    app = QApplication(sys.argv)
    reply = QMessageBox.question(None, args[0], args[1], QMessageBox.Yes|QMessageBox.No)

    conn.send(reply)
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
