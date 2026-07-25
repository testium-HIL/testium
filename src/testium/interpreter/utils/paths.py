import os
import shutil
import sys
import inspect
from pathlib import Path
import testium
from interpreter.utils.params import expanse
import subprocess
import api.testium as tm


def no_window_kwargs():
    # Hide stray child consoles in the frozen Windows GUI exe (console=False has
    # no console to inherit). The wheel/source keeps its console, so leave it.
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def testium_path():

    if getattr(sys, 'frozen', False):
        # Exécuté depuis le .exe
        return sys._MEIPASS

    tp = inspect.getfile(inspect.getmodule(testium))
    return str(Path(tp).parent.resolve())

def subproc_path():
    # py_func and lua_func now live inside the testium package; their cwd
    # is the testium package root, same as testium_path().
    return testium_path()

# Implementation lives in the stdlib-only report helper (shared with
# exporter plugins); kept here for the existing callers.
from runtime.testium_report import prepare_file_to_save


def abs_path_from_file(file):
    abs_file_path = Path(expanse(file))
    if not abs_file_path.is_absolute():
        abs_file_path = Path(tm.gd("test_directory")) / abs_file_path
    abs_file_path = abs_file_path.resolve()
    return abs_file_path


def sys_app_path_win(app_name):
    # shutil.which() rather than `where`: the console output code page is not
    # always the OEM one, so decoding `where` output mangled any non-ASCII
    # path (C:\Users\François\... -> C:\Users\Fran├ºois\...) and discovery
    # failed. which() reads PATH/PATHEXT as str, with no encoding round-trip.
    return shutil.which(app_name) or ""


def sys_app_path_lin(app_name):
    try:
        result = subprocess.run(
            f"which {app_name}", shell=True, capture_output=True, text=True, timeout=10
        )
        data = result.stdout
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        data = ""
    sys_python_bin = data.splitlines()
    for l in sys_python_bin:
        if (f"{app_name}" in l) and not l.startswith("which:"):
            return l
    return ""