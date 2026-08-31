# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Window-session persistence (geometry/state blobs, layout migration) and
startup decisions (log config, file to open).
Pure Python; the toolkit side implements SessionView."""

import os

import interpreter.utils.settings as prefs

# Window-state schema version: bump when docks or toolbars change shape;
# an older blob is rejected and the default layout applies.
STATE_VERSION = 1

_GEOMETRY = prefs.SettingsItem("geometry", bytearray)
_STATE = prefs.SettingsItem("state", bytearray)


class SessionPresenter:
    def __init__(self, view):
        self._view = view

    def restore_geometry(self):
        blob = prefs.settings.value(_GEOMETRY, bytearray())
        if blob:
            self._view.restore_geometry(blob)

    def restore_layout(self):
        """Unknown or older state blob: default layout; the old pane-hiding
        preferences are honored once."""
        blob = prefs.settings.value(_STATE, bytearray())
        restored = bool(blob) and self._view.restore_state(
            bytes(blob), STATE_VERSION)
        if not restored:
            self._view.apply_default_layout()
            if prefs.settings.hide_doc_pane:
                self._view.hide_doc_pane()
            if prefs.settings.hide_log_pane:
                self._view.hide_log_pane()

    def save(self, test_file):
        prefs.settings.set_value(_GEOMETRY,
                                 bytearray(self._view.save_geometry()))
        prefs.settings.set_value(_STATE,
                                 bytearray(self._view.save_state(
                                     STATE_VERSION)))
        if test_file:
            self._view.stash_file_state(test_file)
        self._view.save_column_sizes()
        prefs.settings.sync()

    @staticmethod
    def initial_log_config(cli_log_file):
        """(path, save-to-file, is_cli). A CLI path wins over the stored
        one and is always saved to file."""
        if cli_log_file:
            path = cli_log_file
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), path)
            return path, True, True
        return (prefs.settings.log_file, prefs.settings.log_file_saved,
                False)

    @staticmethod
    def startup_file(cli_file):
        """File to open at startup: the CLI argument (no fallback when it
        is missing on disk), else the most recent file. None otherwise."""
        if cli_file:
            if not os.path.isabs(cli_file):
                cli_file = os.path.join(os.getcwd(), cli_file)
            return cli_file if os.path.isfile(cli_file) else None
        recent = prefs.settings.recent_files
        if recent and os.path.isfile(recent[0]):
            return recent[0]
        return None
