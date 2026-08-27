# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Run I/O plumbing shared by every toolkit: status-queue message
dispatch, output line pump, log tee.
Pure Python; the toolkit side wraps these in its own threads/signals."""


def dispatch_status(message, on_gd_update, on_gd_delete, on_finished,
                    on_status):
    """Route one status-queue message. id None = run finished."""
    msg_type = message.get("type")
    if msg_type == "gd_update":
        on_gd_update(message["key"], message["value"])
    elif msg_type == "gd_delete":
        on_gd_delete(message["key"])
    elif "id" in message and message["id"] is None:
        on_finished()
    else:
        on_status(message)


def pump_lines(stream, emit):
    """Emit the stream's pending output as non-empty lines."""
    for line in stream.read().splitlines():
        if len(line) >= 1:
            emit(line)


class LogTee:
    """Forward writes to the display callback and the optional file
    handle; a file-side error never kills the capture thread."""

    def __init__(self, emit, out=None):
        self._emit = emit
        self.out = out

    def set(self, file_handle):
        self.out = file_handle

    def reset(self):
        self.out = None

    def write(self, m):
        self._emit(m)
        if self.out:
            try:
                self.out.write(m)
            except (UnicodeEncodeError, ValueError, OSError):
                pass

    def writeln(self, m=""):
        self.write(m + "\n")

    def flush(self):
        if self.out:
            self.out.flush()
