# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Textual adapter of the gui.protocols.Scheduler protocol."""


class TextualScheduler:
    def __init__(self, app):
        self._app = app
        self._timers = {}

    def every(self, name, interval_ms, tick):
        self.cancel(name)
        self._timers[name] = self._app.set_interval(
            interval_ms / 1000.0, tick)

    def once(self, name, delay_ms, fire):
        self.cancel(name)

        def fire_once():
            self._timers.pop(name, None)
            fire()

        self._timers[name] = self._app.set_timer(delay_ms / 1000.0, fire_once)

    def cancel(self, name):
        timer = self._timers.pop(name, None)
        if timer is not None:
            timer.stop()
