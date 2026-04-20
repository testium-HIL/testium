import ast
import json
import os
import re
import subprocess
import sys

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QMenu, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout,
)
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QDesktopServices
from PySide6.QtCore import Qt, QUrl, Slot

from main_win.f1_win.f1_win_core import Ui_F1Dialog


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


class GdVarEditDialog(QDialog):
    """JSON editor dialog for dict/list values."""

    def __init__(self, key, value, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit: {key}")
        self.result_value = None

        layout = QVBoxLayout(self)

        self._edit = QTextEdit()
        self._edit.setPlainText(json.dumps(value, indent=2))
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        font.setPointSize(9)
        self._edit.setFont(font)
        layout.addWidget(self._edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.resize(400, 300)

    def _on_ok(self):
        try:
            self.result_value = json.loads(self._edit.toPlainText())
            self.accept()
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Invalid JSON", str(e))


class DialogF1(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_F1Dialog()
        self.ui.setupUi(self)
        self.highlighter = YamlHighlighter(self.ui.TestContentEdit.document())
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool)

        self.ui.ButtLocOpen.clicked.connect(self.on_butlocopen_click)
        self.ui.ButtClose.clicked.connect(self.close)

        self._service = None
        self._key_rows = {}
        self._updating = False
        self._mono_font = QFont("Monospace")
        self._mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._mono_bold_font = QFont("Monospace")
        self._mono_bold_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._mono_bold_font.setBold(True)

        self._setup_vars_tab()

    def _setup_vars_tab(self):
        table = self.ui.varsTable
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 36)
        table.verticalHeader().setVisible(False)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_context_menu)
        table.cellChanged.connect(self._on_cell_changed)
        table.setEnabled(False)
        self.ui.addVarButton.setEnabled(False)
        self.ui.addVarButton.clicked.connect(self._on_add_var)

    def load_initial_vars(self, vars_dict: dict):
        for key, value in vars_dict.items():
            self.gd_var_updated(key, value)

    def set_service(self, service):
        self._service = service
        enabled = service is not None
        self.ui.varsTable.setEnabled(enabled)
        self.ui.addVarButton.setEnabled(enabled)
        if not enabled:
            self._updating = True
            try:
                self.ui.varsTable.setRowCount(0)
            finally:
                self._updating = False
            self._key_rows.clear()

    @Slot(str, object)
    def gd_var_updated(self, key, value):
        if key in self._key_rows:
            self._refresh_row(self._key_rows[key], key, value)
        else:
            self._updating = True
            try:
                row = self.ui.varsTable.rowCount()
                self.ui.varsTable.insertRow(row)
            finally:
                self._updating = False
            self._key_rows[key] = row
            self._refresh_row(row, key, value)

    @Slot(str)
    def gd_var_deleted(self, key):
        if key not in self._key_rows:
            return
        row = self._key_rows.pop(key)
        self._updating = True
        try:
            self.ui.varsTable.removeRow(row)
        finally:
            self._updating = False
        self._key_rows = {k: (r - 1 if r > row else r) for k, r in self._key_rows.items()}

    def _refresh_row(self, row, key, value):
        from PySide6.QtWidgets import QTableWidgetItem
        self._updating = True
        try:
            table = self.ui.varsTable

            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            key_item.setFont(self._mono_bold_font)
            table.setItem(row, 0, key_item)

            display = self._display_value(value)
            val_item = QTableWidgetItem(display)
            val_item.setData(Qt.ItemDataRole.UserRole, value)
            val_item.setToolTip(self._full_tooltip(value))
            val_item.setFont(self._mono_font)
            if self._is_complex(value):
                val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, val_item)

            if self._is_complex(value):
                btn = QPushButton("[…]")
                captured_key = key
                btn.clicked.connect(lambda: self._on_edit_complex(captured_key))
                table.setCellWidget(row, 2, btn)
            else:
                table.setCellWidget(row, 2, None)
                table.setItem(row, 2, QTableWidgetItem())
        finally:
            self._updating = False

    def _is_complex(self, value):
        return isinstance(value, (dict, list))

    def _display_value(self, value):
        if self._is_complex(value):
            text = repr(value)
            return (text[:60] + "…") if len(text) > 60 else text
        return repr(value)

    def _full_tooltip(self, value):
        try:
            text = json.dumps(value, indent=2)
        except (TypeError, ValueError):
            text = repr(value)
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<pre>{escaped}</pre>"

    def _on_cell_changed(self, row, col):
        if self._updating or col != 1 or self._service is None:
            return
        from PySide6.QtWidgets import QTableWidgetItem
        key_item = self.ui.varsTable.item(row, 0)
        val_item = self.ui.varsTable.item(row, 1)
        if key_item is None or val_item is None:
            return
        key = key_item.text()
        text = val_item.text()
        try:
            value = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            value = text
        self._service.set_gd_var(key, value)

    def _on_edit_complex(self, key):
        if key not in self._key_rows:
            return
        val_item = self.ui.varsTable.item(self._key_rows[key], 1)
        if val_item is None:
            return
        value = val_item.data(Qt.ItemDataRole.UserRole)
        dlg = GdVarEditDialog(key, value, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and self._service is not None:
            self._service.set_gd_var(key, dlg.result_value)

    def _on_add_var(self):
        key = self.ui.newKeyEdit.text().strip()
        value_text = self.ui.newValueEdit.text().strip()
        if not key or self._service is None:
            return
        try:
            value = ast.literal_eval(value_text)
        except (ValueError, SyntaxError):
            value = value_text
        self._service.set_gd_var(key, value)
        self.ui.newKeyEdit.clear()
        self.ui.newValueEdit.clear()

    def _on_context_menu(self, pos):
        row = self.ui.varsTable.rowAt(pos.y())
        if row < 0:
            return
        key_item = self.ui.varsTable.item(row, 0)
        if key_item is None or self._service is None:
            return
        key = key_item.text()
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        if menu.exec(self.ui.varsTable.mapToGlobal(pos)) == delete_action:
            self._service.del_gd_var(key)

    def on_butlocopen_click(self):
        file = self.ui.sequenceFileNameLineEdit.text()
        if os.path.exists(file):
            if sys.platform.startswith("win"):
                subprocess.Popen(f'explorer "{file}"')
            else:
                subprocess.Popen(["xdg-open", file])
            QDesktopServices.openUrl(QUrl.fromLocalFile(file))
