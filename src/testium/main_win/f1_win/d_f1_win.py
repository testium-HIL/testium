import os
import sys
import subprocess
import re

from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QDesktopServices
from PySide6.QtCore import Qt, QUrl

from testium.main_win.f1_win.f1_win_core import Ui_F1Dialog


class YamlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(YamlHighlighter, self).__init__(parent)

        self.highlightingRules = []

        # --- KEY formatting (before colon) ---
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#268bd2"))  # Solarized blue
        key_format.setFontWeight(QFont.Bold)
        self.highlightingRules.append((r"^\s*[^:]+(?=:)", key_format))

        # --- VALUE formatting (strings) ---
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#2aa198"))  # teal
        self.highlightingRules.append((r":\s*[^#\n]+", value_format))

        # --- Booleans (true/false) ---
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#b58900"))  # yellow
        bool_format.setFontWeight(QFont.Bold)
        self.highlightingRules.append((r"\b(true|false)\b", bool_format))

        # --- Numbers ---
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#d33682"))  # magenta
        self.highlightingRules.append((r"\b[0-9]+\b", num_format))

        # --- Comments (# ...) ---
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#586e75"))  # gray
        self.highlightingRules.append((r"#.*", comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlightingRules:

            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end-start, fmt)


class DialogF1(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = Ui_F1Dialog()
        self.ui.setupUi(self)
        self.highlighter = YamlHighlighter(self.ui.TestContentEdit.document())
        self.setWindowFlags(
            Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.ui.ButtLocOpen.clicked.connect(self.on_butlocopen_click)
        self.ui.ButtClose.clicked.connect(self.close)

    def on_butlocopen_click(self):
        file = self.ui.sequenceFileNameLineEdit.text()
        if os.path.exists(file):
            if sys.platform.startswith("win"):      # Windows
                subprocess.Popen(f'explorer "{file}"')
            else:                                   # Linux / autres
                subprocess.Popen(["xdg-open", file])
            QDesktopServices.openUrl(QUrl.fromLocalFile(file))