# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Toolkit-neutral presentation tables for the test tree: per-type visual
config, column layout, gutter and highlight precedences, search match rule.
Pure Python; the toolkit side maps names to its own icons and colours."""

# Maps item_name (from TestItemType.item_name) to visual config.
# Keys: icon (required), icon_on (optional 2nd state), expanded, unfoldable, no_breakpoint
ITEM_CONFIG = {
    "unittest":             {"icon": "folder.png",        "icon_on": "folder-open.png", "expanded": True,  "no_breakpoint": True},
    "unittest step":        {"icon": "document.png",                                                        "no_breakpoint": True},
    "pytest":               {"icon": "pytest.png",                                       "expanded": True,  "no_breakpoint": True},
    "pytest step":          {"icon": "pytest.png",                                                          "no_breakpoint": True},
    "Console":              {"icon": "terminal.png",       "unfoldable": False},
    "Console action":       {"icon": "terminal.png"},
    "Cycle":                {"icon": "cycle.png",          "expanded": True},
    "python Function":      {"icon": "python.png"},
    "lua Function":         {"icon": "lua.png"},
    "Report":               {"icon": "report.png"},
    "git repository":       {"icon": "git.png"},
    "Runtime plot":         {"icon": "plot.png"},
    "Runtime plot action":  {"icon": "plot.png"},
    "Group":                {"icon": "folder-orange.png",  "icon_on": "folder-open-orange.png", "expanded": True},
    "Image Dialog":         {"icon": "image.png"},
    "Message Dialog":       {"icon": "info.png"},
    "Let":                  {"icon": "let.png"},
    "Check value":          {"icon": "verif.png"},
    "Note Dialog":          {"icon": "note.png"},
    "Question Dialog":      {"icon": "question.png"},
    "Sleep":                {"icon": "sleep.png"},
    "References Dialog":    {"icon": "label.png"},
    "Value Dialog":         {"icon": "question.png"},
    "Choices Dialog":       {"icon": "label.png"},
    "Run tum":              {"icon": "run.png"},
    "JSON-RPC":             {"icon": "json.png",           "unfoldable": False},
    "JSON-RPC action":      {"icon": "json.png"},
    "Parallel":             {"icon": "parallel.png",        "expanded": True},
    "Parallel branch":      {"icon": "parallel_branch.png", "expanded": True},
}


def make_columns():
    """Per-tree column table (name, index, size). The duration column is
    always present; its visibility follows the preference at run time."""
    return {
        'name':     {'name': 'Name',   'index': 0, 'size': 300},
        'pause':    {'name': '',       'index': 1, 'size': 24},
        'type':     {'name': 'Type',   'index': 2, 'size': 150},
        'status':   {'name': '',       'index': 3, 'size': 50},
        'duration': {'name': 'Time',   'index': 4, 'size': 50},
        'failure':  {'name': 'Fails',  'index': 5, 'size': 50},
        'desc':     {'name': 'Result', 'index': 6, 'size': 100},
    }


# Name-column palette; search forces black text for theme readability.
RUN_BG = "#99FF99"
SEARCH_BG = "#FFE082"
SEARCH_FG = "#000000"


def highlight_style(is_running, is_search_match):
    """'run' > 'search' > None."""
    if is_running:
        return "run"
    if is_search_match:
        return "search"
    return None


def gutter_icon(debug_attach, breakpoint_on, condition):
    """attach > conditional breakpoint > plain breakpoint > None."""
    if debug_attach:
        return "attach_bp" if breakpoint_on else "attach"
    if breakpoint_on and condition:
        return "bp_conditional"
    if breakpoint_on:
        return "bp"
    return None


def matches_search(needle, fields, name, test_type, doc):
    """True if *needle* (lowercase) is in any enabled field (name/type/doc)."""
    if "name" in fields and needle in (name or "").lower():
        return True
    if "type" in fields and needle in (test_type or "").lower():
        return True
    if "doc" in fields and needle in str(doc or "").lower():
        return True
    return False
