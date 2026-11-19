# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Sandbox side of the py_func worker: run a code snippet in a namespace
kept for the life of the process, and complete a name from it."""

import ast
import builtins
import json
import keyword
import linecache
import re
import sys
import traceback

import py_func.tm as tm
from py_func.func_call import func_module

_SOURCE = "<sandbox>"
# load_file(path) imports a script file the way a py_func item does.
_NS = {"__name__": "__sandbox__", "__builtins__": builtins, "tm": tm,
       "load_file": func_module}


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def format_error():
    """Current exception, with the frames of the snippet only."""
    etype, exc, tb = sys.exc_info()
    while tb is not None and tb.tb_frame.f_code.co_filename != _SOURCE:
        tb = tb.tb_next
    return "".join(traceback.format_exception(etype, exc, tb)).rstrip()


def run_code(code):
    """Execute code. A trailing expression gives the returned value."""
    # Lets the traceback show the source lines of the snippet.
    linecache.cache[_SOURCE] = (
        len(code), None, code.splitlines(True), _SOURCE)
    tree = ast.parse(code, _SOURCE, "exec")
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)
    exec(compile(tree, _SOURCE, "exec"), _NS)
    value = None
    if last is not None:
        value = eval(compile(last, _SOURCE, "eval"), _NS)
    return _jsonable(value)


def complete(prefix):
    """Names completing prefix, each one a replacement of the whole prefix."""
    if not re.fullmatch(r"[A-Za-z_][\w.]*|", prefix):
        return []
    head, dot, tail = prefix.rpartition(".")
    if dot:
        obj = _NS
        try:
            parts = head.split(".")
            obj = _NS[parts[0]] if parts[0] in _NS else getattr(builtins, parts[0])
            for part in parts[1:]:
                obj = getattr(obj, part)
            names = dir(obj)
        except Exception:
            return []
    else:
        names = set(_NS) | set(dir(builtins)) | set(keyword.kwlist)
        names.discard("__builtins__")
    return sorted(
        head + dot + n for n in names
        if n.startswith(tail) and (tail.startswith("_") or not n.startswith("_")))
