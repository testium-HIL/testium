"""Helpers for Qt file/directory dialogs.

In Flatpak the native QFileDialog goes through the XDG document portal,
which returns ``/run/user/UID/doc/.../<file>`` and only exposes the
selected file — sibling files (param.yaml, scripts, recent paths in
preferences, ...) are unreachable. Forcing Qt's own non-native dialog
makes it walk the real filesystem mounted via ``--filesystem=home``
and return a regular path.
"""

import os

from PySide6.QtWidgets import QFileDialog


def options():
    """Default ``QFileDialog`` options for the current runtime."""
    opts = QFileDialog.Options()
    if os.path.isfile("/.flatpak-info"):
        opts |= QFileDialog.Option.DontUseNativeDialog
    return opts
