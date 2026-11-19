# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Script sandbox of the test process: run code snippets in a Python, Lua
or Tcl worker, either a process owned by the sandbox or the process of an
active context_id. Output and completion go to the status queue."""

import os
import re
import threading

import api.testium as tm
from interpreter.utils.api_srv import api_request
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.lua_func_exec import LuaFuncExecEngine
from interpreter.utils.py_func_exec import PyFuncExecEngine
from interpreter.utils.tcl_func_exec import TclFuncExecEngine
from interpreter.utils.params import unresolved_names
from runtime.tum_except import ETUMError, ETUMRuntimeError

# language -> (engine class, global holding the context engines, item type)
LANGS = {
    "python": (PyFuncExecEngine, "_py_func_contexts", cst.TYPE_PY_FUNCTION),
    "lua": (LuaFuncExecEngine, "_lua_func_contexts", cst.TYPE_LUA_FUNCTION),
    "tcl": (TclFuncExecEngine, "_tcl_func_contexts", cst.TYPE_TCL_FUNCTION),
}

_START_TIMEOUT = 10
_COMPLETE_TIMEOUT = 2


# ---------- Literals in the target language ----------

def python_literal(value):
    return repr(value)


def _lua_string(s):
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", "\\n").replace("\r", "\\r").replace("\0", "\\0")
    return f'"{s}"'


def lua_literal(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(lua_literal(v) for v in value) + "}"
    if isinstance(value, dict):
        return "{" + ", ".join(
            f"[{lua_literal(k)}] = {lua_literal(v)}"
            for k, v in value.items()) + "}"
    return _lua_string(str(value))


def _tcl_word(s):
    if re.fullmatch(r"[\w./:+-]+", s):
        return s
    depth = 0
    balanced = not s.endswith("\\")
    for i, ch in enumerate(s):
        if ch == "\\":
            balanced = False
            break
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                break
    if balanced and depth == 0:
        return "{" + s + "}"
    out = s
    for ch in ("\\", '"', "$", "[", "]", "{", "}"):
        out = out.replace(ch, "\\" + ch)
    out = out.replace("\n", "\\n").replace("\t", "\\t")
    return f'"{out}"'


def tcl_literal(value):
    if value is None:
        return "{}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[list" + "".join(" " + tcl_literal(v) for v in value) + "]"
    if isinstance(value, dict):
        return "[dict create" + "".join(
            f" {tcl_literal(k)} {tcl_literal(v)}"
            for k, v in value.items()) + "]"
    return _tcl_word(str(value))


def call_code(lang, path, func_name, params):
    """Code loading the script file and calling the function."""
    if lang == "python":
        args = ", ".join(python_literal(p) for p in params)
        return (f"mod = load_file({python_literal(path)})\n"
                f"mod.{func_name}({args})\n")
    if lang == "lua":
        args = ", ".join(lua_literal(p) for p in params)
        return (f"local mod = dofile({_lua_string(path)})\n"
                f"return mod.{func_name}({args})\n")
    args = "".join(" " + tcl_literal(p) for p in params)
    return f"source {_tcl_word(path)}\n{func_name}{args}\n"


def _absolute(path):
    if not os.path.isabs(path):
        path = os.path.join(tm.gd("test_directory", ""), path)
    return os.path.normpath(path)


# ---------- Service ----------

class Sandbox:
    def __init__(self, status_queue, test_set, run_active):
        """run_active: callable, true while a run is executing."""
        self._queue = status_queue
        self._test_set = test_set
        self._run_active = run_active
        self._own = {}
        self._lock = threading.Lock()
        self._thread = None
        self._engine = None

    # ----- status queue -----

    def _emit(self, event, **fields):
        self._queue.put({"type": "sandbox", "event": event, **fields})

    def _request(self, method, params):
        """Worker requests: print goes to the sandbox, the rest to the API."""
        if method == "print":
            text = params if isinstance(params, str) else " ".join(
                str(p) for p in (params or []))
            self._emit("output", text=text)
            return {"result": 0}
        return api_request(method, params)

    # ----- sessions -----

    def _check_lang(self, lang):
        if lang not in LANGS:
            raise ETUMRuntimeError(f"Unknown sandbox language '{lang}'.")

    def _busy(self):
        return self._thread is not None and self._thread.is_alive()

    def _check_available(self):
        if self._run_active() and not self._test_set.isPaused():
            raise ETUMRuntimeError(
                "The sandbox is available when the run is stopped or paused.")

    def _contexts(self, lang):
        contexts = tm.gd(LANGS[lang][1], {})
        return contexts if isinstance(contexts, dict) else {}

    def sessions(self, lang):
        """Active context ids of the language, while the run is paused."""
        self._check_lang(lang)
        if not (self._run_active() and self._test_set.isPaused()):
            return []
        return sorted(str(k) for k, e in self._contexts(lang).items()
                      if e.is_alive())

    def _context_engine(self, lang, session):
        for key, engine in self._contexts(lang).items():
            if str(key) == session:
                return engine
        return None

    def _engine_for(self, lang, session, start=True):
        """Engine of the session. session None = process of the sandbox."""
        if session is not None:
            engine = self._context_engine(lang, session)
            if engine is None or not engine.is_alive():
                raise ETUMRuntimeError(
                    f"The context '{session}' is not active.")
            return engine
        engine = self._own.get(lang)
        if engine is None:
            engine = LANGS[lang][0](self._request, _START_TIMEOUT)
            self._own[lang] = engine
        if not engine.is_alive():
            if not start:
                return None
            engine.start()
            if not engine.wait_ready(_START_TIMEOUT):
                engine.stop()
                engine.join()
                raise ETUMRuntimeError(
                    f"Could not start the {lang} process of the sandbox.")
        return engine

    # ----- commands -----

    def run(self, lang, code, session=None):
        """Start the code in a thread. The result comes as a 'finished'
        event on the status queue."""
        self._check_lang(lang)
        self._check_available()
        with self._lock:
            if self._busy():
                raise ETUMRuntimeError("A sandbox script is already running.")
            engine = self._engine_for(lang, session)
            self._engine = engine
            self._thread = threading.Thread(
                target=self._work, args=(engine, code, session is not None),
                daemon=True)
            self._thread.start()

    def _work(self, engine, code, attached):
        result = None
        error = None
        previous = None
        try:
            if attached:
                previous = engine.set_request_handler(self._request)
            answer = engine.call("run_code", {"code": code})
            if "result" in answer:
                result = answer["result"].get("returned_value")
            else:
                error = str(answer.get("error", "no answer"))
        except ConnectionAbortedError:
            error = "Stopped."
        except Exception as e:  # noqa: BLE001
            error = str(e)
        finally:
            if attached:
                engine.set_request_handler(previous)
            self._engine = None
        self._emit("finished", result=result, error=error)

    def stop(self):
        """Kill the process of the running script."""
        engine = self._engine
        if engine is None:
            return False
        engine.stop()
        engine.join()
        return True

    def reset(self, lang, session=None):
        """Stop the process of the session. The next use starts a new one."""
        self._check_lang(lang)
        if self._busy():
            raise ETUMRuntimeError("A sandbox script is running: stop it first.")
        if session is None:
            engine = self._own.pop(lang, None)
        else:
            engine = self._context_engine(lang, session)
        if engine is not None:
            engine.stop()
            engine.join()

    def complete(self, lang, prefix, session=None):
        """Names of the session completing prefix. Empty when unavailable."""
        self._check_lang(lang)
        if self._busy() or (self._run_active()
                            and not self._test_set.isPaused()):
            return []
        try:
            engine = self._engine_for(lang, session)
            answer = engine.call(
                "complete", {"prefix": prefix}, timeout=_COMPLETE_TIMEOUT)
        except (ETUMError, TimeoutError, ConnectionAbortedError):
            return []
        names = answer.get("result", {}).get("returned_value")
        return [str(n) for n in names] if isinstance(names, list) else []

    def _function_item(self, item):
        for lang, (_, _, item_type) in LANGS.items():
            if item.type() == item_type.item_name:
                return lang
        return None

    def item_call(self, item_id):
        """Code calling the function of an item, parameters expanded."""
        item = self._test_set.findItem(item_id)
        lang = self._function_item(item) if item is not None else None
        if lang is None:
            raise ETUMRuntimeError("This item is not a function item.")
        prms = item._prms
        try:
            path = str(prms.expanse(item.file_name))
            func_name = str(prms.expanse(item.func_name))
            params = prms.expanse(prms.getParamFromList(item.params))
        except ETUMError as e:
            raise ETUMRuntimeError(
                f"Cannot expand the parameters of this item: {e}")
        # Variables set by earlier items do not exist before they run.
        unresolved = unresolved_names([path, func_name, params])
        if not unresolved_names(path):
            path = _absolute(path)
        session = None
        if item._context_id is not None:
            ctx = str(prms.expanse(item._context_id))
            if ctx in self.sessions(lang):
                session = ctx
        return {
            "lang": lang,
            "session": session,
            "file": path,
            "code": call_code(lang, path, func_name, params or []),
            "unresolved": unresolved,
        }

    def scripts(self):
        """Script files of the function items, by language."""
        found = {lang: set() for lang in LANGS}
        for item in self._test_set.items():
            lang = self._function_item(item)
            if lang is None:
                continue
            try:
                path = str(item._prms.expanse(item.file_name))
            except ETUMError:
                continue
            if "$(" in path or "<|" in path:
                continue
            found[lang].add(_absolute(path))
        return {lang: sorted(paths) for lang, paths in found.items()}

    def close(self):
        self.stop()
        for engine in self._own.values():
            engine.stop()
            engine.join()
        self._own.clear()
