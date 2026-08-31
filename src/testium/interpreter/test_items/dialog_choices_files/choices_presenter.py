# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Choices dialog logic: selection tree serialization/restore and the
select-all / fold tri-state transitions."""


def bulk_check_target(box_state):
    """Select-all box: 'checked'/'unchecked' -> state to cascade to every
    row; partial -> None (no action)."""
    return {"checked": True, "unchecked": False}.get(box_state)


def fold_action(box_state):
    """Fold box: (fold everything?, state to pin the box to). Any
    non-unchecked click folds and pins the box checked."""
    if box_state == "unchecked":
        return False, "unchecked"
    return True, "checked"


def checked_state(node, is_checked, is_root=False):
    """Nested {name, checked, choices} description of the selection."""
    subs = [checked_state(node.child(i), is_checked)
            for i in range(node.childCount())]
    if is_root:
        return subs
    res = {"name": node.name, "checked": is_checked(node)}
    if subs:
        res["choices"] = subs
    return res


def apply_checked(choice, parent, set_checked):
    """Restore a previous selection; ignored when the shape differs."""
    if not isinstance(choice, list):
        return
    if len(choice) != parent.childCount():
        return
    for i in range(parent.childCount()):
        if not isinstance(choice[i], dict):
            return
        set_checked(parent.child(i), choice[i].get("checked", True) is True)
        subs = choice[i].get("choices", None)
        if subs is not None:
            apply_checked(subs, parent.child(i), set_checked)
