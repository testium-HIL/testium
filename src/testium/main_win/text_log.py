import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QPlainTextEdit, QSizePolicy
from PySide6.QtGui import QCursor, QDesktopServices, QFont

from main_win.text_log_highlighter import TextLogHighlighter

import libs.testium as tm

class QTextLog(QPlainTextEdit):
    def __init__(self, parent):
        super().__init__(parent)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        font = QFont()
        font.setFamily("Monospace")
        font.setPointSize(8)
        font.setStyleStrategy(QFont.PreferAntialias)
        self.setFont(font)
        self.setLayoutDirection(Qt.LeftToRight)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)
        self.setMaximumBlockCount(100000)
        self.setObjectName("textLog")

        self._test_dir = ""

        self.highlight = TextLogHighlighter(self.document())
        self.setMouseTracking(True)
        self.pattern_file = self.highlight.pattern_file

    def _path_at_pos(self, event):
        """Returns the complete path under the mouse, otherwise none"""
        cursor = self.cursorForPosition(event.pos())
        block = cursor.block()
        text = block.text()
        pos_in_block = cursor.positionInBlock()

        for match in self.pattern_file.finditer(text):
            start, end = match.span()
            if start <= pos_in_block <= end:
                return match.group()
        return None

    def mouseMoveEvent(self, event):
        path = self._path_at_pos(event)
        if path is not None:
            self.viewport().setCursor(QCursor(Qt.PointingHandCursor))
        else:
            self.viewport().setCursor(QCursor(Qt.IBeamCursor))

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            raw_path = self._path_at_pos(event)
            if raw_path is not None:
                path = os.path.expanduser(raw_path)
                if not os.path.isabs(path):
                    if self._test_dir == "":
                        self._test_dir = os.getcwd()
                    path = os.path.join(self._test_dir, path)
                if os.path.exists(path):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                    return  # évite d'insérer du texte si clic
        super().mousePressEvent(event)

    def set_test_dir(self, s):
        self._test_dir = s