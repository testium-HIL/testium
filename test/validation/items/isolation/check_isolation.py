"""Static check that py_func/ and lua_func/ subprocess code does not depend
on testium internals. The contract is:

    py_func/*.py  may import:  py_func.*, runtime.*, plus stdlib/3rd-party
    lua_func/*.lua may require: lua_func/<own files>, plus lua stdlib

Forbidden top-level modules: interpreter, main_win, api, testium.
"""

import ast
import os
import re

FORBIDDEN_PY = {"interpreter", "main_win", "api", "testium"}
FORBIDDEN_LUA = {"interpreter", "main_win", "api", "testium"}


def _collect_py_imports(path):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                out.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                out.add(node.module.split(".")[0])
    return out


def _collect_lua_requires(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return {m.split(".")[0] for m in re.findall(r'require\s*\(?\s*["\']([^"\']+)["\']', text)}


def check_isolation(testium_dir):
    failures = []

    py_dir = os.path.join(testium_dir, "py_func")
    for root, _, files in os.walk(py_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            leaks = _collect_py_imports(p) & FORBIDDEN_PY
            if leaks:
                failures.append(f"py_func/{os.path.relpath(p, py_dir)} leaks: {sorted(leaks)}")

    lua_dir = os.path.join(testium_dir, "lua_func")
    for root, _, files in os.walk(lua_dir):
        for f in files:
            if not f.endswith(".lua"):
                continue
            p = os.path.join(root, f)
            leaks = _collect_lua_requires(p) & FORBIDDEN_LUA
            if leaks:
                failures.append(f"lua_func/{os.path.relpath(p, lua_dir)} leaks: {sorted(leaks)}")

    if failures:
        for line in failures:
            print(f"  - {line}")
        return False
    return True
