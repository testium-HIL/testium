# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Sandbox editor: syntax highlighting rules and completion helpers for
Python, Lua and Tcl. No toolkit import."""

import keyword
import re

LANGUAGES = ("python", "lua", "tcl")
EXTENSIONS = {".py": "python", ".lua": "lua", ".tcl": "tcl"}

# Line states of the highlighter.
NORMAL = 0
PY_TRIPLE_SINGLE = 1
PY_TRIPLE_DOUBLE = 2
LUA_LONG_STRING = 3
LUA_LONG_COMMENT = 4

_LUA_KEYWORDS = (
    "and break do else elseif end false for function goto if in local nil "
    "not or repeat return then true until while").split()
_TCL_KEYWORDS = (
    "after append apply array break catch close continue dict else elseif "
    "error eval expr file for foreach format gets global if incr info join "
    "lappend lassign lindex linsert list llength lmap lrange lreplace "
    "lsearch lset lsort namespace open proc puts read regexp regsub rename "
    "return scan set source split string subst switch then try unset "
    "uplevel upvar variable while").split()

KEYWORDS = {
    "python": set(keyword.kwlist),
    "lua": set(_LUA_KEYWORDS),
    "tcl": set(_TCL_KEYWORDS),
}

API = {
    "python": ["tm.gd", "tm.setgd", "tm.delgd", "load_file"],
    "lua": ["tm.gd", "tm.setgd", "tm.delgd"],
    "tcl": ["tm::gd", "tm::setgd", "tm::delgd", "tm::list", "tm::dict",
            "tm::str", "tm::bool", "tm::null"],
}

_NUMBER = r"\b(?:0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?)\b"
_DQ = r'"(?:\\.|[^"\\])*"?'
_SQ = r"'(?:\\.|[^'\\])*'?"

_TOKENS = {
    "python": re.compile(
        r"(?P<comment>#.*)"
        r"|(?P<triple>[rRbBfFuU]{0,2}(?:'''|\"\"\"))"
        r"|(?P<string>[rRbBfFuU]{0,2}(?:" + _DQ + "|" + _SQ + "))"
        r"|(?P<number>" + _NUMBER + ")"
        r"|(?P<word>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"),
    "lua": re.compile(
        r"(?P<longcomment>--\[\[)"
        r"|(?P<comment>--.*)"
        r"|(?P<longstring>\[\[)"
        r"|(?P<string>" + _DQ + "|" + _SQ + ")"
        r"|(?P<number>" + _NUMBER + ")"
        r"|(?P<word>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"),
    "tcl": re.compile(
        r"(?P<comment>(?:^|(?<=;))\s*#.*)"
        r"|(?P<string>" + _DQ + ")"
        r"|(?P<variable>\$\{[^}]*\}?|\$[\w:]+)"
        r"|(?P<number>" + _NUMBER + ")"
        r"|(?P<word>[A-Za-z_:][\w:]*)"),
}


def _word_kind(lang, word):
    if word in KEYWORDS[lang]:
        return "keyword"
    if word in API[lang] or word == "tm":
        return "api"
    return None


def highlight_line(lang, text, state=NORMAL):
    """Spans of one line: ([(start, length, kind)], state of the next
    line). kind: keyword, api, string, comment, number, variable."""
    spans = []
    pos = 0
    closers = {
        PY_TRIPLE_SINGLE: ("'''", "string"),
        PY_TRIPLE_DOUBLE: ('"""', "string"),
        LUA_LONG_STRING: ("]]", "string"),
        LUA_LONG_COMMENT: ("]]", "comment"),
    }
    while pos <= len(text):
        if state != NORMAL:
            closer, kind = closers[state]
            end = text.find(closer, pos)
            if end < 0:
                if len(text) > pos:
                    spans.append((pos, len(text) - pos, kind))
                return spans, state
            end += len(closer)
            spans.append((pos, end - pos, kind))
            pos = end
            state = NORMAL
            continue
        m = _TOKENS[lang].search(text, pos)
        if m is None:
            break
        kind = m.lastgroup
        start, end = m.span()
        if kind == "triple":
            state = (PY_TRIPLE_SINGLE if m.group().endswith("'''")
                     else PY_TRIPLE_DOUBLE)
            opened = True
        elif kind == "longstring":
            state = LUA_LONG_STRING
            opened = True
        elif kind == "longcomment":
            state = LUA_LONG_COMMENT
            opened = True
        else:
            opened = False
        if opened:
            closer, span_kind = closers[state]
            close = text.find(closer, end)
            if close < 0:
                spans.append((start, len(text) - start, span_kind))
                return spans, state
            close += len(closer)
            spans.append((start, close - start, span_kind))
            state = NORMAL
            pos = close
            continue
        if kind == "word":
            word = m.group()
            word_kind = _word_kind(lang, word)
            if word_kind is None and "." in word:
                # Keyword or API at the head of a dotted name.
                head = word.split(".", 1)[0]
                word_kind = _word_kind(lang, head)
                if word_kind is not None:
                    end = start + len(head)
                elif word.startswith("tm."):
                    word_kind = "api"
            if word_kind is not None:
                spans.append((start, end - start, word_kind))
            end = m.end()
        elif end > start:
            spans.append((start, end - start, kind))
        pos = end if end > pos else pos + 1
    return spans, NORMAL


# ---------- Completion ----------

_PREFIX = {
    "python": re.compile(r"[A-Za-z_][\w.]*$"),
    "lua": re.compile(r"[A-Za-z_][\w.:]*$"),
    "tcl": re.compile(r"\$?[\w:]+$|\$$"),
}

_GD_CONTEXT = {
    "python": re.compile(r"\btm\.(?:gd|setgd|delgd)\(\s*[\"']([\w.-]*)$"),
    "lua": re.compile(r"\btm\.(?:gd|setgd|delgd)\(\s*[\"']([\w.-]*)$"),
    "tcl": re.compile(r"\btm::(?:gd|setgd|delgd)\s+([\w.-]*)$"),
}


def completion_prefix(lang, before_cursor):
    """Name being typed at the end of the text before the cursor."""
    m = _PREFIX[lang].search(before_cursor)
    return m.group() if m else ""


def gd_prefix(lang, before_cursor):
    """Start of a test variable name inside a tm.gd call, None outside."""
    m = _GD_CONTEXT[lang].search(before_cursor)
    return m.group(1) if m else None


def static_words(lang):
    return sorted(KEYWORDS[lang]) + API[lang]


def merge_completions(prefix, *sources, limit=200):
    """Names starting with prefix, without duplicates, sorted."""
    names = set()
    for source in sources:
        for name in source:
            if name.startswith(prefix) and name != prefix:
                names.add(name)
    return sorted(names)[:limit]


def language_of(path):
    """Language of a script file from its extension, None if unknown."""
    dot = path.rfind(".")
    return EXTENSIONS.get(path[dot:].lower()) if dot >= 0 else None
