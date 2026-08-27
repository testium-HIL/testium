# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Path-keyed tree item-state format (fold/check/breakpoint) and the
per-file settings store holding one snapshot per file, LRU-capped.
Pure Python; the toolkit side supplies node accessors and callbacks."""

import hashlib
import os
import time

import interpreter.utils.settings as prefs

FILE_STATES_MAX = 20


# --- Path-keyed item states (fold/check/breakpoint) -----------------------
# Snapshot format: one [key, folded, checked, breakpoint, bp_condition]
# entry per item, JSON-compatible. Key = (type, name, occ) components from
# root to item; occ counts preceding same-named siblings.

def walk_with_keys(parent, children, ident, prefix=()):
    """Yield (node, key); children(node) -> nodes, ident(node) -> (type, name)."""
    seen = {}
    for node in children(parent):
        base = ident(node)
        occ = seen.get(base, 0)
        seen[base] = occ + 1
        key = prefix + (base + (occ,),)
        yield node, key
        yield from walk_with_keys(node, children, ident, key)


def snapshot_states(nodes_with_keys, capture):
    """Build the snapshot. capture(node) -> (folded, checked, breakpoint,
    bp_condition)."""
    states = []
    for node, key in nodes_with_keys:
        folded, checked, breakpoint, condition = capture(node)
        states.append([[list(c) for c in key],
                       folded, checked, breakpoint, condition])
    return states


def states_by_key(states):
    """Decode a snapshot to key -> (folded, checked, breakpoint, condition).
    Length-tolerant: entries saved without bp_condition load unchanged."""
    wanted = {}
    for entry in states:
        key, folded, checked, breakpoint = entry[:4]
        condition = entry[4] if len(entry) > 4 else None
        wanted[tuple(tuple(c) for c in key)] = (
            folded, checked, breakpoint, condition)
    return wanted


def restore_states(states, nodes_with_keys, service, apply_check, *,
                   set_folded, show_skipped, set_checked, set_breakpoint):
    """Restore by path key; unmatched keys keep defaults. Breakpoints and
    enabled states are re-issued to *service* with the new interpreter ids.
    set_breakpoint returns False when the node refuses breakpoints."""
    wanted = states_by_key(states)
    for node, key in nodes_with_keys:
        state = wanted.get(key)
        if state is None:
            continue
        folded, checked, breakpoint, condition = state
        set_folded(node, folded)
        if apply_check:
            if service.get_skipped_state(node.id):
                show_skipped(node)
            else:
                set_checked(node, checked)
                service.set_enabled_state(node.id, checked, unitary=True)
        if breakpoint and set_breakpoint(node, condition):
            service.add_breakpoint(node.id, condition=condition)


class FileStateStore:
    def key(self, path):
        digest = hashlib.sha1(
            os.path.normcase(os.path.abspath(path)).encode()).hexdigest()
        return "itemstates." + digest[:12]

    def stash(self, path, tree_states, log_path, log_saved):
        entry = [os.path.normcase(os.path.abspath(path)), time.time(),
                 tree_states, log_path, log_saved]
        prefs.settings.set_value(
            prefs.SettingsItem(self.key(path), list), entry)
        self.trim()

    def restore(self, path):
        """(tree_states, log_path, log_saved) or None."""
        entry = prefs.settings.value(
            prefs.SettingsItem(self.key(path), list), [])
        if len(entry) < 5:
            return None
        return entry[2], entry[3], entry[4]

    def trim(self):
        names = prefs.settings.option_names("itemstates.")
        if len(names) <= FILE_STATES_MAX:
            return

        def saved_at(name):
            entry = prefs.settings.value(prefs.SettingsItem(name, list), [])
            return entry[1] if len(entry) >= 2 else 0

        for name in sorted(names, key=saved_at)[:len(names)
                                                - FILE_STATES_MAX]:
            prefs.settings.remove_value(name)
