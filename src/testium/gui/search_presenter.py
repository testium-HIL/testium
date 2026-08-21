# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Search navigation state: current match index over an ordered match
list, wrap-around stepping and the counter text."""


class SearchNavigator:
    def __init__(self):
        self._count = 0
        self._idx = 0

    def set_matches(self, count):
        self._count = count
        self._idx = 0

    def clear(self):
        self._count = 0
        self._idx = 0

    @property
    def index(self):
        return self._idx

    def next(self):
        if self._count:
            self._idx = (self._idx + 1) % self._count
        return self._idx

    def prev(self):
        if self._count:
            self._idx = (self._idx - 1) % self._count
        return self._idx

    def count_text(self, active):
        if not active:
            return ""
        if self._count == 0:
            return "0/0"
        return f"{self._idx + 1}/{self._count}"
