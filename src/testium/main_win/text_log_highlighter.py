import re
from PySide6.QtGui import (QColor, QTextCharFormat, QFont, QSyntaxHighlighter)

from gui.open_target import LOG_STYLES, log_rules, FILE_PATTERN


def format(color, style=''):
    """Return a QTextCharFormat with the given attributes.
    """
    _color = QColor()
    _color.setNamedColor(color)

    _format = QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    if 'small' in style:
        _format.setFontPointSize(1)
    return _format


# Tables in gui/open_target.py; only the QTextCharFormat mapping is Qt.
STYLES = {name: format(color, style)
          for name, (color, style) in LOG_STYLES.items()}


class TextLogHighlighter (QSyntaxHighlighter):
    """Syntax highlighter for the run log."""

    def __init__(self, document):
        super().__init__(document)
        self.rules = [(exp, STYLES[name]) for exp, name in log_rules()]
        self.pattern_file = FILE_PATTERN

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        for expression, format in self.rules:
            for match in re.finditer(expression, text):
                start, end = match.span()
                self.setFormat(start, end-start, format)

        self.setCurrentBlockState(0)
