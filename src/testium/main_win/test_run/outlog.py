'''
Created on 4 nov. 2013

@author: francois.d
'''

from PySide6 import QtGui
from PySide6.QtCore import QObject, Signal


import sys

class OutLog(QObject):
    logToBeAppended = Signal(str)

    def __init__(self, out=None):
        super().__init__(None)
        self.out = out

    def set(self, file_handle):
        self.out = file_handle

    def reset(self):
        self.out = None

    def write(self, m):
        self.logToBeAppended.emit(m)

        if self.out:
            self.out.write(m)

    def writeln(self, m=""):
        self.write(m + "\n")

    def flush(self):
        if self.out:
            self.out.flush()