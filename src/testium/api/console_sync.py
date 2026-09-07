# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Completion markers for shell consoles.

The exec action appends a per-call marker to the command line; seeing
the marker in the output means the command is finished. The sent line
never contains the marker in one piece (the shell reassembles it at
execution time) and the expected pattern anchors it at line start, so a
raw echo of the command line can never match.
"""

import re
import uuid

DIALECTS = ("sh", "cmd", "powershell")


def new_marker_id():
    return uuid.uuid4().hex[:12]


def wrap_command(cmd, marker_id, dialect):
    """Single line running *cmd* then printing the marker on its own line."""
    if dialect == "sh":
        # Adjacent-quote split; leading blank line guards against output
        # without a trailing newline; ';' prints the marker even on failure.
        return "{}; printf '\\n%s\\n' '@TSTM:''{}@'".format(cmd, marker_id)
    if dialect == "cmd":
        # Caret split (consumed at execution); 'echo(' emits a blank line;
        # '&' runs regardless of the command result.
        return "{} & echo( & echo @TS^TM:{}@".format(cmd, marker_id)
    if dialect == "powershell":
        # String concatenation split; an expression statement prints itself.
        return "{}; ''; ('@TSTM:'+'{}@')".format(cmd, marker_id)
    raise ValueError("unknown console dialect {!r}".format(dialect))


def completion_regex(marker_id):
    """Marker at line start. The optional ':digits' field is reserved for
    a future exit code: emitting it will not change completion detection."""
    return r"(?:^|[\r\n])@TSTM:" + marker_id + r"(?::\d+)?@"


def strip_marker(data, marker_id):
    """Command output without the final marker line."""
    return re.sub(r"[\r\n]*@TSTM:" + marker_id + r"(?::\d+)?@$", "", data)


def guess_dialect(protocol, shell):
    """Default dialect for a console: guessed from the shell for the
    protocols that spawn one, 'none' for the device protocols."""
    if protocol == "ssh":
        return "sh"
    if protocol == "terminal":
        name = (shell or "").lower()
        if "powershell" in name or "pwsh" in name:
            return "powershell"
        if "cmd" in name:
            return "cmd"
        return "sh"
    return "none"
