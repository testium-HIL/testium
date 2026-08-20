"""Run-level execution controller shared by every TestItem of a run.

Stepping granularity is the existing pause point: the @test_run wrapper spins
on _is_paused before each item body, at every depth. A step command arms a
mode + reference depth, releases the paused item, and the next item whose
depth matches pauses itself in run_test_init.

The controller also carries the run-level pause request (Pause lets the
current step finish and stops the run before the next one), the jump state
(unwind to the root, re-enter in seek mode, pause on the target) and the
last executed leaf (jump_back).

Accessed from two threads: the control-command daemon thread (arm/step) and
the execution thread(s), including parallel branches (notify/should_pause).
"""

import threading

MODE_INTO = "into"
MODE_OVER = "over"
MODE_OUT = "out"


class JumpRequested(Exception):
    """Control-flow signal: unwind to the root and re-enter in seek mode.
    Not an ETUM error: must never be swallowed by user-error handlers."""


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
        # Run-level pause request: a level, not one-shot, so under parallel
        # every branch's next item pauses.
        self._pause_requested = False
        # Jump: armed target, then seek route (ids of the target's ancestors).
        # pause flag False = run the target and pause on the next item.
        self._jump_target = None
        self._jump_pause = True
        self._seek_target = None
        self._seek_pause = True
        self._seek_route = None
        # Last leaf whose body ran (jump_back).
        self._last_executed = None

    def notify_paused(self, item):
        """Register the item spinning in its pause loop."""
        with self._lock:
            self._current = item

    def clear_paused(self, item):
        with self._lock:
            if self._current is item:
                self._current = None

    def current(self):
        with self._lock:
            return self._current

    def step(self, mode):
        """Arm a step from the currently paused item.

        Returns the item to release (cont), or None. With no paused item,
        'over' degrades to 'into' (used to start a run paused on its first
        item) and 'out' degrades to a plain continue (nothing armed).
        """
        with self._lock:
            # An armed step keeps its depth semantics: the pause level must
            # not pause the very next item at any depth.
            self._pause_requested = False
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

    # --- run-level pause ---

    def request_pause(self):
        with self._lock:
            self._pause_requested = True

    def clear_pause(self):
        with self._lock:
            self._pause_requested = False

    def pause_requested(self):
        with self._lock:
            return self._pause_requested

    # --- jump ---

    def arm_jump(self, target, pause_on_target=True):
        """Arm a jump to *target*; the paused item's spin picks it up."""
        with self._lock:
            self._jump_target = target
            self._jump_pause = pause_on_target

    def jump_pending(self):
        with self._lock:
            return self._jump_target is not None

    def cancel_jump(self):
        """Drop a jump not yet picked up by the paused item's spin."""
        with self._lock:
            self._jump_target = None

    def take_jump(self):
        """Root only: convert the pending jump into an active seek.
        Returns True if a jump was converted."""
        with self._lock:
            if self._jump_target is None:
                return False
            self._seek_target = self._jump_target
            self._seek_pause = self._jump_pause
            self._jump_target = None
            route = set()
            p = self._seek_target.parent()
            while p is not None:
                route.add(p.id())
                p = p.parent()
            self._seek_route = route
            return True

    def seek_active(self):
        with self._lock:
            return self._seek_target is not None

    def seek_skip(self, item):
        """Seek active and this item is neither the target nor one of its
        ancestors: fall through without executing."""
        with self._lock:
            if self._seek_target is None:
                return False
            return (item is not self._seek_target
                    and item.id() not in self._seek_route)

    def arrived(self, item):
        """Seek active and this item is the target: clear the seek and
        report the one-shot arrival. Returns False, 'pause' (the item
        pauses on itself) or 'run' (the item runs; the next one pauses
        through an armed 'into' step)."""
        with self._lock:
            if self._seek_target is not item:
                return False
            self._seek_target = None
            self._seek_route = None
            if self._seek_pause:
                return 'pause'
            self._mode = MODE_INTO
            self._ref_depth = None
            return 'run'

    # --- jump_back support ---

    def note_executed(self, item):
        with self._lock:
            self._last_executed = item

    def last_executed(self):
        with self._lock:
            return self._last_executed

    def reset(self):
        with self._lock:
            self._mode = None
            self._ref_depth = None
            self._current = None
            self._pause_requested = False
            self._jump_target = None
            not_reached = self._seek_target is not None
            self._seek_target = None
            self._seek_route = None
            self._last_executed = None
        return not_reached
