import os
import sys
import inspect
from pathlib import Path
import testium
from interpreter.utils.params import expanse
import subprocess
import libs.testium as tm


def testium_path():
    tp = inspect.getfile(inspect.getmodule(testium))
    return str(Path(tp).parent.resolve())


def prepare_file_to_save(file_name, file_ext=""):
    iname = file_name
    if file_ext != "":
        iname = os.path.splitext(file_name)[0] + file_ext

    if os.path.isfile(iname):
        i = 0
        fname = iname
        while os.path.isfile(fname):
            i += 1
            fname = iname + "-" + str(i) + ".saved"
        os.rename(iname, fname)
    return iname


def abs_path_from_file(file):
    abs_file_path = Path(expanse(file))
    if not abs_file_path.is_absolute():
        abs_file_path = Path(tm.gd("test_directory")) / abs_file_path
    abs_file_path = abs_file_path.resolve()
    return abs_file_path


def sys_encoding():
    if tm.OS() == "Windows":
        enc = 'oem'
    else:
        enc = 'utf-8'
    return enc


def _python_version(path: str):
    cmd = f'"{path}" -c "import sys; print(sys.version_info[:3])"'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding=sys_encoding(),
            timeout=10
        )
        data = result.stdout
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as e:
        tm.print_debug(str(e))
        data = ""
    return eval(data)


def _lua_version(path: str):
    cmd = f'"{path}" -v'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding=sys_encoding(),
            timeout=10
        )
        # Under windows, the output is on stderr
        data = result.stdout or result.stderr
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as e:
        data = ""
    try:
        vers = ((data.split(" "))[1]).split(".")
        if len(vers) != 3:
            vers = (0,0,0)
    except:
        vers = (0,0,0)
    return tuple(vers)


def is_python3(python_path):
    try:
        v = _python_version(python_path)
        if v[0] == 3:
            res = True
    except:
        res = False

    return res


def is_lua51(lua_path):
    res = False
    v = _lua_version(lua_path)
    if (v[0] == "5") and (v[1] >= "1"):
        res = True
    return res


def _sys_app_path_win(app_name):
    try:
        result = subprocess.run(
            f"where {app_name}",
            shell=True,
            capture_output=True,
            text=True,
            encoding="oem",
            timeout=10
        )
        data = result.stdout
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        data = ""
    sys_python_path = data.splitlines()
    for l in sys_python_path:
        if f"{app_name}.exe" in l:
            return l
    return ""


def _sys_app_path_lin(app_name):
    try:
        result = subprocess.run(
            f"which {app_name}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        data = result.stdout
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        data = ""
    sys_python_path = data.splitlines()
    for l in sys_python_path:
        if (
            (f"{app_name}" in l)
            and not l.startswith("which:")
        ):
            return l
    return ""


def sys_python_path():
    sys_python_path = tm.gd("_sys_python_path", "")
    if sys_python_path != "":
        return sys_python_path

    cur_os = tm.OS()
    if cur_os == "Windows":
        func = _sys_app_path_win
    else:
        func = _sys_app_path_lin

    exe=["python3", "python"]
    for e in exe:
        sys_python_path = func(e)
        if sys_python_path == "":
            continue
        if not is_python3(sys_python_path):
            sys_python_path = ""
            continue

    tm.setgd("_sys_python_path", sys_python_path)
    return sys_python_path


def sys_lua_path():
    sys_lua_path = tm.gd("_sys_lua_path", "")
    if sys_lua_path != "":
        return sys_lua_path

    cur_os = tm.OS()
    if cur_os == "Windows":
        func = _sys_app_path_win
    else:
        func = _sys_app_path_lin

    sys_lua_path = func("lua")
    if (sys_lua_path != "") and not is_lua51(sys_lua_path):
        tm.print_debug(f"'{sys_lua_path}' not a lua 5.1 min.")
        sys_lua_path = ""

    tm.setgd("_sys_lua_path", sys_lua_path)
    return sys_lua_path
