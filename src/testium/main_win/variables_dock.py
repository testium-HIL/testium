# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Variables dock: the global dict table with filter, edition and the
expression tester. Display only; the logic lives in
gui/variables_presenter.py."""

import json

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDockWidget, QGroupBox,
    QHBoxLayout, QHeaderView, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)

from gui.variables_presenter import VariablesPresenter
from main_win.expression_info import expression_info_button


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
        self._updating = False
        self._presenter = VariablesPresenter(self, lambda: self._service)
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

        self.filter_edit = QLineEdit(body)
        self.filter_edit.setPlaceholderText("Filter variables by name")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self._filter_values_cb = QCheckBox("values", body)
        self._filter_values_cb.setToolTip("Also match on the variable value")
        self._filter_values_cb.toggled.connect(self._on_filter_changed)
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

        # Fixed height: the vertical slack goes to the table.
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

    # --- entry points ---

    def set_service(self, service):
        self._service = service
        self._presenter.set_available(service is not None)

    def load_initial_vars(self, vars_dict: dict):
        self._presenter.load_initial_vars(vars_dict)

    @Slot(str, object)
    def gd_var_updated(self, key, value):
        self._presenter.var_updated(key, value)

    @Slot(str)
    def gd_var_deleted(self, key):
        self._presenter.var_deleted(key)

    # --- VariablesView implementation -------------------------------------

    def set_enabled(self, enabled):
        self.varsTable.setEnabled(enabled)
        self.addVarButton.setEnabled(enabled)
        self._expr_edit.setEnabled(enabled)
        self._expr_button.setEnabled(enabled)
        if not enabled:
            self._expr_result.clear()
            self._expr_result.setStyleSheet("")

    def clear_rows(self):
        self._updating = True
        try:
            self.varsTable.setRowCount(0)
        finally:
            self._updating = False

    def insert_row(self, row):
        self._updating = True
        try:
            self.varsTable.insertRow(row)
        finally:
            self._updating = False

    def remove_row(self, row):
        self._updating = True
        try:
            self.varsTable.removeRow(row)
        finally:
            self._updating = False

    def set_row(self, row, key, display, tooltip, value, editable):
        self._updating = True
        try:
            table = self.varsTable

            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            key_item.setFont(self._mono_bold_font)
            table.setItem(row, 0, key_item)

            val_item = QTableWidgetItem(display)
            val_item.setData(Qt.ItemDataRole.UserRole, value)
            val_item.setToolTip(tooltip)
            val_item.setFont(self._mono_font)
            if not editable:
                val_item.setFlags(
                    val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, val_item)

            if not editable:
                btn = QPushButton("[…]")
                captured_key = key
                btn.clicked.connect(
                    lambda: self._on_edit_complex(captured_key))
                table.setCellWidget(row, 2, btn)
            else:
                table.setCellWidget(row, 2, None)
                table.setItem(row, 2, QTableWidgetItem())
        finally:
            self._updating = False

    def set_row_hidden(self, row, hidden):
        self.varsTable.setRowHidden(row, hidden)

    def row_display(self, row):
        item = self.varsTable.item(row, 1)
        return item.text() if item is not None else ""

    def show_expr_result(self, text, is_error):
        self._expr_result.setStyleSheet("color: #b71c1c;" if is_error else "")
        self._expr_result.setPlainText(text)

    # --- widget slots ------------------------------------------------------

    def _on_expr_entered(self):
        self._presenter.evaluate(self._expr_edit.toPlainText())

    def _on_filter_changed(self, _arg=None):
        self._presenter.set_filter(self.filter_edit.text(),
                                   self._filter_values_cb.isChecked())

    def _on_cell_changed(self, row, col):
        if self._updating or col != 1:
            return
        key_item = self.varsTable.item(row, 0)
        val_item = self.varsTable.item(row, 1)
        if key_item is None or val_item is None:
            return
        self._presenter.edit_value(key_item.text(), val_item.text())

    def _on_edit_complex(self, key):
        # Looked up at click time: deletions above may have shifted rows.
        val_item = None
        for row in range(self.varsTable.rowCount()):
            key_item = self.varsTable.item(row, 0)
            if key_item is not None and key_item.text() == key:
                val_item = self.varsTable.item(row, 1)
                break
        if val_item is None:
            return
        value = val_item.data(Qt.ItemDataRole.UserRole)
        dlg = GdVarEditDialog(key, value, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._presenter.set_value(key, dlg.result_value)

    def _on_add_var(self):
        if self._presenter.add_var(self.newKeyEdit.text(),
                                   self.newValueEdit.text()):
            self.newKeyEdit.clear()
            self.newValueEdit.clear()

    def _on_context_menu(self, pos):
        row = self.varsTable.rowAt(pos.y())
        if row < 0:
            return
        key_item = self.varsTable.item(row, 0)
        if key_item is None:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        if menu.exec(self.varsTable.mapToGlobal(pos)) == delete_action:
            self._presenter.delete_var(key_item.text())
