# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Pure helpers over tree nodes exposing the Qt-item duck type
(childCount()/child(i), isExpanded()/setExpanded(), setCheckState()).
No toolkit import: shared by the main tree and the dialog trees."""


def fold_recursively(parent, folded, unfoldable=None):
    """Fold or unfold every descendant with children. Ordered for a single
    visual update: folding sets the parent first, unfolding the children
    first."""
    for i in range(parent.childCount()):
        child = parent.child(i)
        if child.childCount() == 0:
            continue
        if unfoldable is not None and not unfoldable(child):
            continue
        if folded:
            child.setExpanded(False)
            fold_recursively(child, folded, unfoldable)
        else:
            fold_recursively(child, folded, unfoldable)
            child.setExpanded(True)


def cascade_check(node, state, column=0):
    """Apply *state* to the node and its whole subtree."""
    node.setCheckState(column, state)
    for i in range(node.childCount()):
        cascade_check(node.child(i), state, column)
