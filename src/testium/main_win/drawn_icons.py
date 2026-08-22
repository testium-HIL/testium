# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Small icons drawn in code — same in every icon theme."""

from PySide6.QtCore import Qt
from PySide6.QtCore import QRect
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon,
                           QPainter, QPixmap)

_cache = {}


def follow_icon():
    """Target reticle: follow the running step."""
    icon = _cache.get("follow")
    if icon is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = painter.pen()
        pen.setColor(QColor(60, 150, 60))
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(14, 14, 36, 36)
        painter.drawLine(32, 2, 32, 20)
        painter.drawLine(32, 44, 32, 62)
        painter.drawLine(2, 32, 20, 32)
        painter.drawLine(44, 32, 62, 32)
        painter.setBrush(QColor(60, 150, 60))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(27, 27, 10, 10)
        painter.end()
        icon = QIcon(pixmap)
        _cache["follow"] = icon
    return icon


def search_icon():
    """Magnifier: open the step search bar."""
    icon = _cache.get("search")
    if icon is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = painter.pen()
        pen.setColor(QColor(70, 70, 70))
        pen.setWidth(7)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(10, 10, 30, 30)
        painter.drawLine(37, 37, 56, 56)
        painter.end()
        icon = QIcon(pixmap)
        _cache["search"] = icon
    return icon


def expression_icon():
    """Formula glyph: evaluate an expression."""
    icon = _cache.get("expression")
    if icon is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        # Plot blue, like the color theme.
        painter.setPen(QColor(29, 138, 197))
        font = QFont("serif")
        font.setItalic(True)
        font.setBold(True)
        font.setPixelSize(46)
        painter.setFont(font)
        painter.drawText(QRect(4, 2, 34, 60), Qt.AlignCenter, "f")
        font2 = QFont("serif")
        font2.setItalic(True)
        font2.setPixelSize(30)
        painter.setFont(font2)
        painter.drawText(QRect(32, 22, 28, 40), Qt.AlignCenter, "x")
        painter.end()
        icon = QIcon(pixmap)
        _cache["expression"] = icon
    return icon


def variables_icon():
    """$( ) glyph: the testium variable syntax."""
    icon = _cache.get("variables")
    if icon is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        # Cycle purple, like the color theme.
        painter.setPen(QColor(155, 38, 175))
        font = QFont("monospace")
        font.setBold(True)
        size = 40
        font.setPixelSize(size)
        metrics = QFontMetrics(font)
        while metrics.horizontalAdvance("$( )") > 60 and size > 10:
            size -= 2
            font.setPixelSize(size)
            metrics = QFontMetrics(font)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, "$( )")
        painter.end()
        icon = QIcon(pixmap)
        _cache["variables"] = icon
    return icon
