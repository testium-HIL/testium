# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Per-item result text and dated failure history shown by the tree's
Result column."""

MAX_ENTRIES = 1000


class ResultHistory:
    def __init__(self):
        self._current = {}
        self._entries = {}

    def set_current(self, item_id, message):
        self._current[item_id] = message

    def record_failure(self, item_id, date, message):
        """A failure keeps a dated entry on top of the current text."""
        self._current[item_id] = message
        entries = self._entries.setdefault(item_id, [])
        entries.insert(0, (date, message))
        del entries[MAX_ENTRIES:]

    def current(self, item_id):
        return self._current.get(item_id, "")

    def entries(self, item_id):
        return list(self._entries.get(item_id, ()))

    def clear(self):
        self._current.clear()
        self._entries.clear()
