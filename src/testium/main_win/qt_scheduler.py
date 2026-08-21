# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Scheduler protocol on QTimer: named repeating/one-shot timers."""

from PySide6.QtCore import QTimer


class QtScheduler:
    def __init__(self, parent=None):
        self._parent = parent
        self._timers = {}

    def _timer(self, name, single_shot, interval_ms, slot):
        old = self._timers.pop(name, None)
        if old is not None:
            old.stop()
            old.deleteLater()
        t = QTimer(self._parent)
        t.setSingleShot(single_shot)
        t.setInterval(interval_ms)
        t.timeout.connect(slot)
        self._timers[name] = t
        t.start()

    def every(self, name, interval_ms, tick):
        self._timer(name, False, interval_ms, tick)

    def once(self, name, delay_ms, fire):
        self._timer(name, True, delay_ms, fire)

    def cancel(self, name):
        t = self._timers.pop(name, None)
        if t is not None:
            t.stop()
            t.deleteLater()
