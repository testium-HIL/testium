# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Debug rules: per-item context-menu availability, breakpoint-condition
edition, debug-output preference and its effective-value sync.
Pure Python; the toolkit side implements DebugView."""

from dataclasses import dataclass

import interpreter.utils.settings as prefs
from interpreter.utils.constants import TestItemType as cst
from runtime.tum_except import ETUMRuntimeError

_PARALLEL_TYPES = (cst.TYPE_PARALLEL.item_name,
                   cst.TYPE_PARALLEL_BRANCH.item_name)


@dataclass(frozen=True)
class ItemMenuState:
    """Availability of the per-item debug actions."""
    attach_enabled: bool
    attach_checked: bool
    condition_enabled: bool
    jump_enabled: bool


def item_menu_state(item_type, debug_attach, no_breakpoint, is_skipped,
                    is_paused, self_and_ancestor_types):
    """Attach only applies to py_func items. Jump needs a paused run, a
    non-skipped item, and no Parallel/ParallelBranch in the ancestry."""
    is_py_func = item_type == cst.TYPE_PY_FUNCTION.item_name
    in_parallel = any(t in _PARALLEL_TYPES for t in self_and_ancestor_types)
    return ItemMenuState(
        attach_enabled=is_py_func,
        attach_checked=is_py_func and debug_attach,
        condition_enabled=not no_breakpoint,
        jump_enabled=is_paused and not is_skipped and not in_parallel)


def breakpoint_condition_change(is_breakpoint, text):
    """New condition (None = plain breakpoint), or False when nothing
    changes. An emptied condition downgrades an existing breakpoint."""
    text = (text or "").strip()
    if text:
        return text
    if is_breakpoint:
        return None
    return False


class DebugPresenter:
    def __init__(self, view, service):
        """service: zero-argument callable returning the current
        TestControllerService, or None (it is swapped on reload)."""
        self._view = view
        self._service = service

    def on_debug_output_toggled(self, checked):
        prefs.settings.debug_output = checked
        self._view.set_step_actions_visible(checked)
        service = self._service()
        if service is not None:
            service.set_gd_var("test_debug", bool(checked))

    def sync_debug_output(self, gd_vars):
        """Show the effective test_debug value; the preference is unchanged."""
        effective = bool(gd_vars.get("test_debug", False))
        if effective != self._view.debug_output_checked():
            self._view.set_debug_output_checked(effective)
            self._view.set_step_actions_visible(effective)

    def set_debug_attach(self, item_id, enabled):
        self._service().set_debug_attach(item_id, enabled)

    def add_breakpoint(self, item_id, condition=None):
        self._service().add_breakpoint(item_id, condition=condition)

    def jump_to(self, item_id):
        try:
            self._service().jump_to(item_id)
        except ETUMRuntimeError as e:
            self._view.show_transient_message(str(e))
