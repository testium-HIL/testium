import re
from PySide6.QtGui import (QColor, QTextCharFormat, QFont, QSyntaxHighlighter)

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


# Syntax styles that can be shared by all languages
STYLES = {
    'keyword': format('red', 'bold'),
    'keyword2': format('green'),
    'keyword3': format('blue'),
    'keyword4': format('orange'),
    'keyword5': format('darkCyan'),
    'keyword6': format('darkBlue', 'bold'),
    'timestamp': format('lightGrey', 'small'),
    'operator': format('darkRed'),
    'brace': format('darkMagenta'),
    'defclass': format('black', 'bold'),
    'string': format('darkslategray'),
    'string2': format('darkCyan'),
    'comment': format('darkCyan', 'italic'),
    'self': format('black', 'italic'),
    'numbers': format('darkBlue'),
}


class TextLogHighlighter (QSyntaxHighlighter):
    """Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = [
        'assert', 'ASSERT', 'Assert'
        'fail', 'FAIL', 'Fail', 'Failed', 'FAILED',
        'error', 'ERROR', 'Error',
        'Error', 'raise'
    ]

    keywords2 = [
        'PASS', 'Passed', 'PASSED', 'OK', 'ok'
    ]

    keywords3 = [
        'step', 'STEP', 'Step',
        'True', 'true', 'TRUE',
        'False', 'false', 'FALSE',
    ]

    keywords4 = [
        'WARN', 'warning', 'Warning', 'WARNING',
        'DEBUG'
    ]

    keywords5 = [
        'INFO',
        'Skipped', 'skipped', 'SKIPPED',
        'Skip', 'skip', 'SKIP'
    ]
    keywords6 = [
        'None'
    ]

    # Python operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        '\+', '-', '\*', '/', '//', '\%', '\*\*',
        # In-place
        '\+=', '-=', '\*=', '/=', '\%=',
        # Bitwise
        '\^', '\|', '\&', '\~', '>>', '<<',
    ]

    # Python braces
    braces = [
        '\{', '\}', '\(', '\)', '\[', '\]',
    ]

    def __init__(self, document):
        super().__init__(document)

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, STYLES['keyword'])
                  for w in TextLogHighlighter.keywords]
        rules += [(r'\b%s\b' % w, STYLES['keyword2'])
                  for w in TextLogHighlighter.keywords2]
        rules += [(r'\b%s\b' % w, STYLES['keyword3'])
                  for w in TextLogHighlighter.keywords3]
        rules += [(r'\b%s\b' % w, STYLES['keyword4'])
                  for w in TextLogHighlighter.keywords4]
        rules += [(r'\b%s\b' % w, STYLES['keyword5'])
                  for w in TextLogHighlighter.keywords5]
        rules += [(r'\b%s\b' % w, STYLES['keyword6'])
                  for w in TextLogHighlighter.keywords6]
        rules += [(r'%s' % o, STYLES['operator'])
                  for o in TextLogHighlighter.operators]
        rules += [(r'%s' % b, STYLES['brace'])
                  for b in TextLogHighlighter.braces]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', STYLES['self']),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', STYLES['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", STYLES['string']),

            # # 'def' followed by an identifier
            # (r'\bdef\b\s*(\w+)', 1, STYLES['defclass']),
            # # 'class' followed by an identifier
            # (r'\bclass\b\s*(\w+)', 1, STYLES['defclass']),

            # From '#' until a newline
            (r'#[^\n]*', STYLES['comment']),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b',
             STYLES['numbers']),

            # Timestamp
            (r"@@[0-9]*@@", STYLES['timestamp']),
        ]

        # Build a QRegularExpression for each pattern
        self.rules = rules

        forbidden = r"[^\s\n\{\[\"]+"
        self.pattern_file = re.compile(
            r"(?:[A-Za-z]:\\" + forbidden + "|"   # Windows C:\...
            r"~" + forbidden + "|"                # ~/...
            r"\.{0,2}/" + forbidden + "|"         # ./..., ../...
            r"/" + forbidden + "|"                # /...
            r"[A-Za-z0-9_\-\.]+/" + forbidden + ")"
        )
        # self.format_file = QTextCharFormat()
        # self.format_file.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        # self.format_file.setForeground(Qt.blue)

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        for expression, format in self.rules:
            for match in re.finditer(expression, text):
                start, end = match.span()
                self.setFormat(start, end-start, format)

            # for match in self.pattern_file.finditer(text):
            #     start, end = match.span()
            #     self.setFormat(start, end-start, self.format_file)

        self.setCurrentBlockState(0)
