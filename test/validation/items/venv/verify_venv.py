import os
import sys

import py_func.tm as tm


def _norm(p):
    # normpath + normcase, without resolving symlinks. realpath() would
    # follow the venv's ``python3`` symlink to ``/usr/bin/python3.X`` and
    # defeat the comparison.
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def _venv_dir():
    # python_bin is at ``<venv>/(bin|Scripts)/python*`` so the venv root
    # is two levels above the executable.
    exe = tm.gd("python_bin", "")
    if not exe:
        return ""
    return os.path.dirname(os.path.dirname(_norm(exe)))


def check_sys_executable():
    """py_func subprocess: sys.executable must match the configured python_bin."""
    expected = _norm(tm.gd("python_bin", ""))
    actual = _norm(sys.executable)
    if expected and actual == expected:
        return True
    return (
        -1,
        f"sys.executable={actual!r} differs from python_bin={expected!r}",
    )


def check_sys_prefix_in_venv():
    """py_func subprocess: sys.prefix must match the venv root derived
    from python_bin (two levels up from the executable)."""
    venv = _venv_dir()
    if not venv:
        return (-1, "python_bin is not set in the global dict")
    actual = _norm(sys.prefix)
    if actual == venv:
        return True
    return (
        -1,
        f"sys.prefix={actual!r} is not the validation venv {venv!r}",
    )


def check_is_venv():
    """py_func subprocess: confirm we are inside a venv, i.e. sys.prefix
    differs from sys.base_prefix. This catches the case where python_bin
    happens to be a system interpreter and the path-based check would
    pass trivially."""
    actual = _norm(sys.prefix)
    base = _norm(sys.base_prefix)
    if actual != base:
        return True
    return (
        -1,
        f"sys.prefix == sys.base_prefix == {actual!r}: not running in a venv",
    )
