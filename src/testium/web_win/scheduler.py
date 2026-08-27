# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""NiceGUI adapter of the gui.protocols.Scheduler protocol. app.timer
runs server-side, independent of connected clients."""

from nicegui import app


class NiceScheduler:
    def __init__(self):
        self._timers = {}

    def every(self, name, interval_ms, tick):
        self.cancel(name)
        self._timers[name] = app.timer(interval_ms / 1000.0, tick)

    def once(self, name, delay_ms, fire):
        self.cancel(name)

        def fire_once():
            self._timers.pop(name, None)
            fire()

        self._timers[name] = app.timer(delay_ms / 1000.0, fire_once,
                                       once=True)

    def cancel(self, name):
        timer = self._timers.pop(name, None)
        if timer is not None:
            timer.cancel()
