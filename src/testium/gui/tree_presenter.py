# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Per-test-file interface state: tree item states and log-file choice,
stored in the settings under one key per file, LRU-capped."""

import hashlib
import os
import time

import interpreter.utils.settings as prefs

FILE_STATES_MAX = 20


class FileStateStore:
    def key(self, path):
        digest = hashlib.sha1(
            os.path.normcase(os.path.abspath(path)).encode()).hexdigest()
        return "itemstates." + digest[:12]

    def stash(self, path, tree_states, log_path, log_saved):
        entry = [os.path.normcase(os.path.abspath(path)), time.time(),
                 tree_states, log_path, log_saved]
        prefs.settings.set_value(
            prefs.SettingsItem(self.key(path), list), entry)
        self.trim()

    def restore(self, path):
        """(tree_states, log_path, log_saved) or None."""
        entry = prefs.settings.value(
            prefs.SettingsItem(self.key(path), list), [])
        if len(entry) < 5:
            return None
        return entry[2], entry[3], entry[4]

    def trim(self):
        names = prefs.settings.option_names("itemstates.")
        if len(names) <= FILE_STATES_MAX:
            return

        def saved_at(name):
            entry = prefs.settings.value(prefs.SettingsItem(name, list), [])
            return entry[1] if len(entry) >= 2 else 0

        for name in sorted(names, key=saved_at)[:len(names)
                                                - FILE_STATES_MAX]:
            prefs.settings.remove_value(name)
