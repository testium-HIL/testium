"""Single-step execution controller shared by every TestItem of a run.

Stepping granularity is the existing pause point: the @test_run wrapper spins
on _is_paused before each item body, at every depth. A step command arms a
mode + reference depth, releases the paused item, and the next item whose
depth matches pauses itself in run_test_init.

Accessed from two threads: the control-command daemon thread (arm/step) and
the execution thread(s), including parallel branches (notify/should_pause).
"""

import threading

MODE_INTO = "into"
MODE_OVER = "over"
MODE_OUT = "out"


def depth(item):
    """Number of ancestors: root = 0, top-level items = 1."""
    d = 0
    p = item.parent()
    while p is not None:
        d += 1
        p = p.parent()
    return d


class StepController:
    def __init__(self):
        self._lock = threading.Lock()
        self._mode = None
        self._ref_depth = None
        self._current = None

    def notify_paused(self, item):
        """Register the item spinning in its pause loop."""
        with self._lock:
            self._current = item

    def clear_paused(self, item):
        with self._lock:
            if self._current is item:
                self._current = None

    def step(self, mode):
        """Arm a step from the currently paused item.

        Returns the item to release (cont), or None. With no paused item,
        'over' degrades to 'into' (used to start a run paused on its first
        item) and 'out' degrades to a plain continue (nothing armed).
        """
        with self._lock:
            item = self._current
            if item is None:
                if mode == MODE_OUT:
                    return None
                self._mode = MODE_INTO
                self._ref_depth = None
            else:
                self._mode = mode
                self._ref_depth = depth(item)
            self._current = None
            return item

    def should_pause(self, item):
        """Called from run_test_init: True if this item consumes the armed
        step and must pause. First matching item wins (defines the behavior
        under parallel branches)."""
        with self._lock:
            if self._mode is None or item.parent() is None:
                return False
            if self._mode == MODE_INTO:
                match = True
            elif self._mode == MODE_OVER:
                match = depth(item) <= self._ref_depth
            else:  # MODE_OUT
                match = depth(item) < self._ref_depth
            if match:
                self._mode = None
                self._ref_depth = None
            return match

    def disarm(self):
        with self._lock:
            self._mode = None
            self._ref_depth = None

    def reset(self):
        with self._lock:
            self._mode = None
            self._ref_depth = None
            self._current = None
