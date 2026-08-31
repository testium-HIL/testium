# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Expression tester dock: evaluate an expression against the current
variables. Display only; the logic lives in gui/variables_presenter.py."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QDockWidget, QHBoxLayout, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

from gui.variables_presenter import ExpressionPresenter
from main_win.expression_info import expression_info_button


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


class ExpressionDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Expression", parent)
        self.setObjectName("expressionDock")
        self._service = None
        self._presenter = ExpressionPresenter(self, lambda: self._service)

        mono = QFont("Monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        mono.setPointSizeF(max(7.0, self.font().pointSizeF() - 1))

        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.expr_edit = _ExprEdit(self._on_expr_entered)
        self.expr_edit.setPlaceholderText("$(var) == 3   (Enter evaluates)")
        self.expr_edit.setFont(mono)
        self.expr_edit.setEnabled(False)
        self._expr_button = QPushButton("Evaluate")
        self._expr_button.clicked.connect(self._on_expr_entered)
        self._expr_button.setEnabled(False)
        self._expr_result = QPlainTextEdit()
        self._expr_result.setReadOnly(True)
        self._expr_result.setFont(mono)
        self._expr_result.setPlaceholderText("Result")
        row = QHBoxLayout()
        row.addWidget(self.expr_edit, 1)
        row.addWidget(expression_info_button(
            self, extra="<br>A lone <code>$(name)</code> shows the value "
                        "without evaluating it.<br><b>Enter</b> evaluates, "
                        "<b>Shift+Enter</b> inserts a new line."),
            0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._expr_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row, 1)
        layout.addWidget(self._expr_result, 1)

        self.setWidget(body)

    def set_service(self, service):
        self._service = service
        enabled = service is not None
        self.expr_edit.setEnabled(enabled)
        self._expr_button.setEnabled(enabled)
        if not enabled:
            self._expr_result.clear()
            self._expr_result.setStyleSheet("")

    def show_expr_result(self, text, is_error):
        self._expr_result.setStyleSheet("color: #b71c1c;" if is_error else "")
        self._expr_result.setPlainText(text)

    def _on_expr_entered(self):
        self._presenter.evaluate(self.expr_edit.toPlainText())
