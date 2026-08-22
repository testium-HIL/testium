# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Small icons drawn in code — same in every icon theme."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QPainter,
                           QPainterPath, QPen, QPixmap)

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


def _centered_text_path(font, text):
    """Path of *text*, centered on the origin."""
    path = QPainterPath()
    path.addText(0, 0, font, text)
    box = path.boundingRect()
    path.translate(-box.center().x(), -box.center().y())
    return path


def expression_icon():
    """Formula glyph: evaluate an expression."""
    icon = _cache.get("expression")
    if icon is None:
        # Drawn at 256 px: crisp once scaled down. Fill plus outline:
        # bold alone is too thin at toolbar size.
        pixmap = QPixmap(256, 256)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        ink = QColor(255, 183, 77)
        pen = QPen(ink)
        pen.setWidth(10)
        font = QFont("serif")
        font.setItalic(True)
        font.setBold(True)
        font.setPixelSize(200)
        path = _centered_text_path(font, "f")
        path.translate(84, 122)
        font2 = QFont(font)
        font2.setPixelSize(122)
        path2 = _centered_text_path(font2, "x")
        path2.translate(184, 174)
        for glyph in (path, path2):
            painter.fillPath(glyph, ink)
            painter.strokePath(glyph, pen)
        painter.end()
        icon = QIcon(pixmap)
        _cache["expression"] = icon
    return icon


def variables_icon():
    """$( ) glyph: the testium variable syntax."""
    icon = _cache.get("variables")
    if icon is None:
        # Sans $( ) around an italic serif x, shared baseline, sized to
        # fill the 256 px canvas.
        pixmap = QPixmap(256, 256)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(186, 104, 200))
        gap = 2

        def fonts(px):
            # Full-height dollar; smaller parentheses and italic x keep
            # the four glyphs inside the square.
            f_dollar = QFont("sans")
            f_dollar.setWeight(QFont.Black)
            f_dollar.setStretch(88)
            f_dollar.setPixelSize(px)
            f_paren = QFont(f_dollar)
            f_paren.setPixelSize(int(px * 0.52))
            f_x = QFont("serif")
            f_x.setBold(True)
            f_x.setItalic(True)
            f_x.setPixelSize(int(px * 0.50))
            return f_dollar, f_paren, f_x

        def tights(f_dollar, f_paren, f_x):
            m_d = QFontMetrics(f_dollar)
            m_p = QFontMetrics(f_paren)
            m_x = QFontMetrics(f_x)
            return (m_d.tightBoundingRect("$"), m_p.tightBoundingRect("("),
                    m_x.tightBoundingRect("x"), m_p.tightBoundingRect(")"))

        t_d, t_1, t_x, t_2 = tights(*fonts(120))
        total = (t_d.width() + t_1.width() + t_x.width() + t_2.width()
                 + 3 * gap)
        px = int(120 * min(250 / total, 235 / t_d.height()))
        f_dollar, f_paren, f_x = fonts(px)
        t_d, t_1, t_x, t_2 = tights(f_dollar, f_paren, f_x)
        base_y = 128 - t_d.y() - t_d.height() / 2
        x = (256 - (t_d.width() + t_1.width() + t_x.width() + t_2.width()
                    + 3 * gap)) / 2
        for text, font, tight in (("$", f_dollar, t_d), ("(", f_paren, t_1),
                                  ("x", f_x, t_x), (")", f_paren, t_2)):
            painter.setFont(font)
            painter.drawText(QPointF(x - tight.x(), base_y), text)
            x += tight.width() + gap
        painter.end()
        icon = QIcon(pixmap)
        _cache["variables"] = icon
    return icon
