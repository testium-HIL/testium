# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Log text semantics shared by every toolkit (keyword styles, clickable
path pattern, timestamp marker) and the open-a-path cascade.
Pure Python; the toolkit side maps styles to its own formats and opens
URLs as the last fallback."""

import os
import re
import shlex
import subprocess

import interpreter.utils.settings as prefs
from interpreter.utils import bins


# --- log <-> tree correlation ---------------------------------------------

def timestamp_marker(ts):
    """Marker written in the log at each item start; searched to scroll."""
    return "@@{}@@".format(ts)


# --- log highlighting tables ----------------------------------------------
# Style name -> (colour name, 'bold'/'italic'/'small' flags string).
LOG_STYLES = {
    'keyword': ('red', 'bold'),
    'keyword2': ('green', ''),
    'keyword3': ('blue', ''),
    'keyword4': ('orange', ''),
    'keyword5': ('darkCyan', ''),
    'keyword6': ('darkBlue', 'bold'),
    'timestamp': ('lightGrey', 'small'),
    'operator': ('darkRed', ''),
    'brace': ('darkMagenta', ''),
    'defclass': ('black', 'bold'),
    'string': ('darkslategray', ''),
    'string2': ('darkCyan', ''),
    'comment': ('darkCyan', 'italic'),
    'self': ('black', 'italic'),
    'numbers': ('darkBlue', ''),
}

_KEYWORDS = {
    'keyword': [
        'assert', 'ASSERT', 'Assert'
        'fail', 'FAIL', 'Fail', 'Failed', 'FAILED',
        'error', 'ERROR', 'Error',
        'Error', 'raise'
    ],
    'keyword2': [
        'PASS', 'Passed', 'PASSED', 'OK', 'ok'
    ],
    'keyword3': [
        'step', 'STEP', 'Step',
        'True', 'true', 'TRUE',
        'False', 'false', 'FALSE',
    ],
    'keyword4': [
        'WARN', 'warning', 'Warning', 'WARNING',
        'DEBUG'
    ],
    'keyword5': [
        'INFO',
        'Skipped', 'skipped', 'SKIPPED',
        'Skip', 'skip', 'SKIP'
    ],
    'keyword6': [
        'None'
    ],
}

_OPERATORS = [
    '=',
    '==', '!=', '<', '<=', '>', '>=',
    r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',
    r'\+=', '-=', r'\*=', '/=', r'\%=',
    r'\^', r'\|', r'\&', r'\~', '>>', '<<',
]

_BRACES = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']


def log_rules():
    """(regex, style name) pairs, in application order."""
    rules = []
    for style, words in _KEYWORDS.items():
        rules += [(r'\b%s\b' % w, style) for w in words]
    rules += [(o, 'operator') for o in _OPERATORS]
    rules += [(b, 'brace') for b in _BRACES]
    rules += [
        (r'\bself\b', 'self'),
        (r'"[^"\\]*(\\.[^"\\]*)*"', 'string'),
        (r"'[^'\\]*(\\.[^'\\]*)*'", 'string'),
        (r'#[^\n]*', 'comment'),
        (r'\b[+-]?[0-9]+[lL]?\b', 'numbers'),
        (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 'numbers'),
        (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 'numbers'),
        (r"@@[0-9]*@@", 'timestamp'),
    ]
    return rules


_FORBIDDEN = r"[^\s\n\{\[\"]+"
# Clickable paths: Windows C:\..., ~/..., ./..., /..., dir/...
FILE_PATTERN = re.compile(
    r"(?:[A-Za-z]:\\" + _FORBIDDEN + "|"
    r"~" + _FORBIDDEN + "|"
    r"\.{0,2}/" + _FORBIDDEN + "|"
    r"/" + _FORBIDDEN + "|"
    r"[A-Za-z0-9_\-\.]+/" + _FORBIDDEN + ")"
)


# --- open-a-path cascade --------------------------------------------------

def resolve_log_path(raw_path, test_dir):
    """Path for a clicked log entry: ~ expanded, relative joined to the
    test directory (cwd when empty). None when missing on disk."""
    path = os.path.expanduser(raw_path)
    if not os.path.isabs(path):
        path = os.path.join(test_dir or os.getcwd(), path)
    return path if os.path.exists(path) else None


def open_path(path, line=None):
    """Open *path*: editor template ({file}/{line}, when *line* is given),
    else the host opener. False -> the toolkit opens it as a URL."""
    if line is not None and prefs.settings.editor_cmd:
        try:
            argv = [p.format(file=path, line=line)
                    for p in shlex.split(prefs.settings.editor_cmd)]
            subprocess.Popen(
                bins.host_console_command(argv, os.path.dirname(path) or "."))
            return True
        except (KeyError, ValueError, IndexError, OSError):
            pass
    return bins.host_open_path(path)
