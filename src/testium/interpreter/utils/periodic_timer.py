
from threading import Timer
from time import monotonic

class PeriodicTimer:
    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.execution = None
        self.active = False
        self.t0 = 0

    def exec_periodically(self):
        if self.active:
            self.function()
            time_elapsed = monotonic() - self.t0
            time_waiting = max(0.01, self.interval-time_elapsed)
            self.execution = Timer(time_waiting, self.exec_periodically)
            self.t0 = self.t0 + self.interval
            self.execution.start()

    def start(self):
        if not self.active:
            self.active = True
            self.t0 = monotonic()
            self.execution = Timer(self.interval, self.exec_periodically)
            self.execution.start()

    def stop(self):
        if self.active:
            self.execution.cancel()
            self.active = False