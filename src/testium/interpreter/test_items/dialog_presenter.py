# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Shared logic of the test-item dialogs (spawned child processes):
auto-close decision and frozen-stream mute."""

AUTO_CLOSE_MS = 2000


def accepts(auto_result):
    """True when the auto_result argument asks to accept the dialog."""
    return auto_result is not None and auto_result.lower() in ("ok", "yes")


def mute_frozen_streams():
    """cx_freeze flush workaround: no-op every standard stream."""
    import sys
    if not hasattr(sys, "frozen"):
        return

    class _NoStream:
        def write(self, data):
            pass

        def read(self, data):
            pass

        def flush(self):
            pass

        def close(self):
            pass

    for name in ("stdout", "stderr", "stdin",
                 "__stdout__", "__stderr__", "__stdin__"):
        setattr(sys, name, _NoStream())
