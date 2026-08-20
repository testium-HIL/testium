# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Shared info button for the expression input fields."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QToolButton, QToolTip

from interpreter.utils.icons import icon_prefix

EXPRESSION_HELP = (
    "<b>Expression</b><br>"
    "Plain Python, evaluated against the current variables.<br>"
    "<code>$(name)</code> is replaced by the variable value.<br>"
    "The <code>&lt;| ... |&gt;</code> markers are accepted but not needed."
)


def expression_info_button(parent=None, extra=""):
    """Flat info button: full explanation on hover and on click."""
    btn = QToolButton(parent)
    icon = QIcon()
    icon.addPixmap(QPixmap(icon_prefix() + "/info.png"))
    btn.setIcon(icon)
    btn.setAutoRaise(True)
    btn.setCursor(Qt.WhatsThisCursor)
    text = EXPRESSION_HELP + extra
    btn.setToolTip(text)
    btn.clicked.connect(lambda: QToolTip.showText(
        btn.mapToGlobal(btn.rect().bottomLeft()), text, btn))
    return btn
