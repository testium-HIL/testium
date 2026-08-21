# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Variables dock: the global dict table with filter, edition and the
expression tester."""

import ast
import json

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDockWidget, QGroupBox,
    QHBoxLayout, QHeaderView, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)
from PySide6.QtGui import QFontMetrics

from main_win.expression_info import expression_info_button
from runtime.tum_except import ETUMRuntimeError
import re


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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
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


class _ExprEdit(QPlainTextEdit):
    """Enter evaluates, Shift+Enter inserts a newline."""

    def __init__(self, on_enter, parent=None):
        super().__init__(parent)
        self._on_enter = on_enter

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._on_enter()
            return
        super().keyPressEvent(event)


class VariablesDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Variables", parent)
        self.setObjectName("variablesDock")
        self._service = None
        self._key_rows = {}
        self._updating = False
        small = max(7.0, self.font().pointSizeF() - 1)
        self._mono_font = QFont("Monospace")
        self._mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._mono_font.setPointSizeF(small)
        self._mono_bold_font = QFont(self._mono_font)
        self._mono_bold_font.setBold(True)

        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Filter row: hides rows whose name (optionally value) doesn't match.
        self._filter_text = ""
        self.filter_edit = QLineEdit(body)
        self.filter_edit.setPlaceholderText("Filter variables by name")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self._filter_values_cb = QCheckBox("values", body)
        self._filter_values_cb.setToolTip("Also match on the variable value")
        self._filter_values_cb.toggled.connect(lambda _c: self._apply_filter())
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.filter_edit)
        filter_row.addWidget(self._filter_values_cb)
        layout.addLayout(filter_row)

        self.varsTable = QTableWidget(0, 3, body)
        self.varsTable.setHorizontalHeaderLabels(["Key", "Value", ""])
        self.varsTable.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.varsTable.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.varsTable.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed)
        self.varsTable.setColumnWidth(2, 36)
        self.varsTable.verticalHeader().setVisible(False)
        self.varsTable.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.varsTable.customContextMenuRequested.connect(self._on_context_menu)
        self.varsTable.cellChanged.connect(self._on_cell_changed)
        self.varsTable.setEnabled(False)
        layout.addWidget(self.varsTable, 1)

        self.newKeyEdit = QLineEdit(body)
        self.newKeyEdit.setPlaceholderText("New key")
        self.newValueEdit = QLineEdit(body)
        self.newValueEdit.setPlaceholderText("Value")
        self.addVarButton = QPushButton("+", body)
        self.addVarButton.setMaximumWidth(30)
        self.addVarButton.setEnabled(False)
        self.addVarButton.clicked.connect(self._on_add_var)
        add_row = QHBoxLayout()
        add_row.addWidget(self.newKeyEdit)
        add_row.addWidget(self.newValueEdit)
        add_row.addWidget(self.addVarButton)
        layout.addLayout(add_row)

        # Expression tester, fixed height: the slack goes to the table.
        metrics = QFontMetrics(self._mono_font)
        self._expr_edit = _ExprEdit(self._on_expr_entered)
        self._expr_edit.setPlaceholderText("$(var) == 3   (Enter evaluates)")
        self._expr_edit.setFont(self._mono_font)
        self._expr_edit.setFixedHeight(metrics.lineSpacing() * 3 + 12)
        self._expr_edit.setEnabled(False)
        self._expr_button = QPushButton("Evaluate")
        self._expr_button.clicked.connect(self._on_expr_entered)
        self._expr_button.setEnabled(False)
        self._expr_result = QPlainTextEdit()
        self._expr_result.setReadOnly(True)
        self._expr_result.setFont(self._mono_font)
        self._expr_result.setPlaceholderText("Result")
        self._expr_result.setFixedHeight(metrics.lineSpacing() * 4 + 12)
        box = QGroupBox("Expression tester", body)
        box_layout = QVBoxLayout(box)
        expr_row = QHBoxLayout()
        expr_row.addWidget(self._expr_edit, 1)
        expr_row.addWidget(expression_info_button(
            self, extra="<br>A lone <code>$(name)</code> shows the value "
                        "without evaluating it.<br><b>Enter</b> evaluates, "
                        "<b>Shift+Enter</b> inserts a new line."),
            0, Qt.AlignmentFlag.AlignTop)
        expr_row.addWidget(self._expr_button, 0, Qt.AlignmentFlag.AlignTop)
        box_layout.addLayout(expr_row)
        box_layout.addWidget(self._expr_result)
        box.setSizePolicy(QSizePolicy.Policy.Preferred,
                          QSizePolicy.Policy.Fixed)
        layout.addWidget(box)

        self.setWidget(body)

    # --- service / rows ---

    def set_service(self, service):
        self._service = service
        enabled = service is not None
        self.varsTable.setEnabled(enabled)
        self.addVarButton.setEnabled(enabled)
        self._expr_edit.setEnabled(enabled)
        self._expr_button.setEnabled(enabled)
        if not enabled:
            self._expr_result.clear()
            self._expr_result.setStyleSheet("")
            self._updating = True
            try:
                self.varsTable.setRowCount(0)
            finally:
                self._updating = False
            self._key_rows.clear()

    def load_initial_vars(self, vars_dict: dict):
        for key, value in vars_dict.items():
            self.gd_var_updated(key, value)

    @Slot(str, object)
    def gd_var_updated(self, key, value):
        if key in self._key_rows:
            self._refresh_row(self._key_rows[key], key, value)
        else:
            self._updating = True
            try:
                row = self.varsTable.rowCount()
                self.varsTable.insertRow(row)
            finally:
                self._updating = False
            self._key_rows[key] = row
            self._refresh_row(row, key, value)
        self._apply_filter_row(self._key_rows[key])

    @Slot(str)
    def gd_var_deleted(self, key):
        if key not in self._key_rows:
            return
        row = self._key_rows.pop(key)
        self._updating = True
        try:
            self.varsTable.removeRow(row)
        finally:
            self._updating = False
        self._key_rows = {k: (r - 1 if r > row else r)
                          for k, r in self._key_rows.items()}
        self._apply_filter()

    def _refresh_row(self, row, key, value):
        self._updating = True
        try:
            table = self.varsTable

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
                val_item.setFlags(
                    val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
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

    # --- filtering ---

    def _on_filter_changed(self, text):
        self._filter_text = text.strip().lower()
        self._apply_filter()

    def _apply_filter(self):
        for row in range(self.varsTable.rowCount()):
            self._apply_filter_row(row)

    def _apply_filter_row(self, row):
        needle = self._filter_text
        if not needle:
            self.varsTable.setRowHidden(row, False)
            return
        table = self.varsTable
        key_item = table.item(row, 0)
        hay = key_item.text().lower() if key_item else ""
        if self._filter_values_cb.isChecked():
            val_item = table.item(row, 1)
            if val_item is not None:
                hay += "\n" + val_item.text().lower()
        table.setRowHidden(row, needle not in hay)

    # --- value formatting ---

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
        escaped = (text.replace("&", "&amp;")
                   .replace("<", "&lt;").replace(">", "&gt;"))
        return f"<pre>{escaped}</pre>"

    # --- edition ---

    def _on_cell_changed(self, row, col):
        if self._updating or col != 1 or self._service is None:
            return
        key_item = self.varsTable.item(row, 0)
        val_item = self.varsTable.item(row, 1)
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
        val_item = self.varsTable.item(self._key_rows[key], 1)
        if val_item is None:
            return
        value = val_item.data(Qt.ItemDataRole.UserRole)
        dlg = GdVarEditDialog(key, value, self)
        if dlg.exec() == QDialog.DialogCode.Accepted \
                and self._service is not None:
            self._service.set_gd_var(key, dlg.result_value)

    def _on_add_var(self):
        key = self.newKeyEdit.text().strip()
        value_text = self.newValueEdit.text().strip()
        if not key or self._service is None:
            return
        try:
            value = ast.literal_eval(value_text)
        except (ValueError, SyntaxError):
            value = value_text
        self._service.set_gd_var(key, value)
        self.newKeyEdit.clear()
        self.newValueEdit.clear()

    def _on_context_menu(self, pos):
        row = self.varsTable.rowAt(pos.y())
        if row < 0:
            return
        key_item = self.varsTable.item(row, 0)
        if key_item is None or self._service is None:
            return
        key = key_item.text()
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        if menu.exec(self.varsTable.mapToGlobal(pos)) == delete_action:
            self._service.del_gd_var(key)

    # --- expression tester ---

    @staticmethod
    def _error_text(e):
        """Keep the cause only: drop the control-command wrapper and the
        ETUM banner line."""
        text = str(e)
        m = re.search(r"failed: '(.*)'$", text, re.S)
        if m:
            text = m.group(1)
        lines = [l for l in text.splitlines()
                 if l.strip() != "TUM runtime error:"]
        return "\n".join(lines).strip()

    def _on_expr_entered(self):
        expr = self._expr_edit.toPlainText().strip()
        if not expr or self._service is None:
            return
        try:
            result = self._service.eval_expr(expr)
        except ETUMRuntimeError as e:
            self._expr_result.setStyleSheet("color: #b71c1c;")
            self._expr_result.setPlainText(self._error_text(e))
            return
        self._expr_result.setStyleSheet("")
        self._expr_result.setPlainText(repr(result))
