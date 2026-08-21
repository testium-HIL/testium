# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Test-item dock: type, source file and YAML content of the selected
item. Replaces the Test item tab of the retired F1 window."""

import os
import re
import subprocess
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (QColor, QDesktopServices, QFont,
                           QSyntaxHighlighter, QTextCharFormat)
from PySide6.QtWidgets import (QDockWidget, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QTextEdit, QToolButton,
                               QVBoxLayout, QWidget)

from interpreter.utils import bins


class YamlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(YamlHighlighter, self).__init__(parent)

        self.highlightingRules = []

        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#268bd2"))
        key_format.setFontWeight(QFont.Bold)
        self.highlightingRules.append((r"^\s*[^:]+(?=:)", key_format))

        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#2aa198"))
        self.highlightingRules.append((r":\s*[^#\n]+", value_format))

        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#b58900"))
        bool_format.setFontWeight(QFont.Bold)
        self.highlightingRules.append((r"\b(true|false)\b", bool_format))

        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#d33682"))
        self.highlightingRules.append((r"\b[0-9]+\b", num_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#586e75"))
        self.highlightingRules.append((r"#.*", comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlightingRules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class ItemDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Test item", parent)
        self.setObjectName("itemDock")

        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        form = QFormLayout()
        self.typeLineEdit = QLineEdit(body)
        self.typeLineEdit.setReadOnly(True)
        form.addRow(QLabel("Test step type"), self.typeLineEdit)
        file_row = QHBoxLayout()
        self.sequenceFileNameLineEdit = QLineEdit(body)
        self.sequenceFileNameLineEdit.setReadOnly(True)
        self.ButtLocOpen = QToolButton(body)
        self.ButtLocOpen.setText("...")
        self.ButtLocOpen.setToolTip("Open the file location")
        self.ButtLocOpen.clicked.connect(self.on_butlocopen_click)
        file_row.addWidget(self.sequenceFileNameLineEdit, 1)
        file_row.addWidget(self.ButtLocOpen)
        form.addRow(QLabel("Test file name"), file_row)
        layout.addLayout(form)

        self.TestContentEdit = QTextEdit(body)
        self.TestContentEdit.setReadOnly(True)
        mono = QFont("Monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        self.TestContentEdit.setFont(mono)
        self.highlighter = YamlHighlighter(self.TestContentEdit.document())
        layout.addWidget(self.TestContentEdit, 1)

        self.setWidget(body)

    def show_item(self, tree_item):
        self.typeLineEdit.setText(tree_item.test_type)
        self.sequenceFileNameLineEdit.setText(tree_item.seq_filename)
        if tree_item.content is not None and tree_item.content != "":
            self.TestContentEdit.setHtml(tree_item.content)
        else:
            self.TestContentEdit.setText("")

    def on_butlocopen_click(self):
        file = self.sequenceFileNameLineEdit.text()
        if not os.path.exists(file):
            return
        if bins.host_open_path(file):
            return
        if sys.platform.startswith("win"):
            subprocess.Popen(f'explorer "{file}"')
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file))
