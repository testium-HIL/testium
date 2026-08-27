# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Decodes engine status messages into StatusUpdate display directives
and owns the per-item run state (failures, timestamps, global verdict).
Pure Python; the toolkit side applies StatusUpdate to its widgets."""

from dataclasses import dataclass
from typing import Optional

from api.testium import timestamp_as_sec
from gui.result_history import ResultHistory
from interpreter.test_items.test_result import TestValue


@dataclass
class StatusUpdate:
    """Display directives for one engine status message. None = untouched."""
    icon: Optional[str] = None          # "success" | "success_after_fail" | "fail"
    failure_count: Optional[int] = None
    result: Optional[tuple] = None      # (one-line text, tooltip or None)
    highlight: Optional[bool] = None    # True set, False reset
    follow: bool = False                # scroll to the follow target
    duration_text: Optional[str] = None
    paused: bool = False


class StatusPresenter:
    def __init__(self):
        self.history = ResultHistory()
        self.global_success = True
        self.follow = False
        self._failed = set()
        self._failure_count = {}
        self._timestamp = {}

    def reset(self):
        """Full reset on tree rebuild: interpreter ids are reallocated."""
        self.clear_run_marks()
        self.global_success = True
        self._timestamp.clear()

    def clear_run_marks(self):
        """Run start: drop result texts and failure counters."""
        self.history.clear()
        self._failed.clear()
        self._failure_count.clear()

    def timestamp(self, item_id):
        """First 'started' timestamp of the item, -1 before it ran."""
        return self._timestamp.get(item_id, -1)

    def decode(self, status):
        """Engine status dict -> StatusUpdate; None without a target item."""
        if status.get('id', 0) <= 0:
            return None
        item_id = status['id']
        upd = StatusUpdate()

        if 'value' in status:
            is_success = status['value'] == TestValue.SUCCESS.value
            is_norun = status['value'] == TestValue.NORUN.value
            if is_success:
                # A success after an earlier failure keeps the orange mark.
                upd.icon = ("success_after_fail" if item_id in self._failed
                            else "success")
            elif not is_norun:
                upd.icon = "fail"
                self._failed.add(item_id)
                count = self._failure_count.get(item_id, 0) + 1
                self._failure_count[item_id] = count
                upd.failure_count = count
                self.global_success = False
            if 'message' in status:
                if (not is_success) and (not is_norun):
                    if status['message'] != '':
                        self.history.record_failure(
                            item_id, status['date'], status['message'])
                elif not is_norun:
                    self.history.set_current(item_id, status['message'])
                upd.result = self.result_display(item_id)
        elif 'message' in status:
            self.history.set_current(item_id, status['message'])
            upd.result = self.result_display(item_id)

        if 'status' in status:
            st = status['status'].lower()
            if st == 'started':
                upd.highlight = True
                self._latch_timestamp(item_id, status['timestamp'])
                upd.follow = self.follow
            elif st == 'paused':
                upd.paused = True
            else:
                upd.highlight = False

        if 'duration' in status:
            upd.duration_text = '{:.1f}'.format(
                timestamp_as_sec(status['duration']))
        return upd

    def result_display(self, item_id):
        """(one-line text, full tooltip): multi-line text would change the
        row height."""
        text = self.history.current(item_id)
        return (" ".join(text.split()), text if text else None)

    def _latch_timestamp(self, item_id, val):
        # First positive value wins.
        if (self._timestamp.get(item_id, -1) < 0) and (val > 0):
            self._timestamp[item_id] = val

    @staticmethod
    def follow_target(item, ancestors):
        """Topmost collapsed (ancestor, is_expanded) from parent to root,
        else the item: a collapsed group is never expanded by follow."""
        target = item
        for ancestor, expanded in ancestors:
            if not expanded:
                target = ancestor
        return target
