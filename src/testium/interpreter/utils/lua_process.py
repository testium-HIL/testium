import os
import sys
import shutil
import subprocess
import socket

import libs.testium as tm
from lib.jrpc import JsonRpcClient
from interpreter.utils.paths import subproc_path
from lib.tum_except import ETUMRuntimeError
from interpreter.utils.paths import sys_app_path_lin, sys_app_path_win

def _lua_version(path: str):
    cmd = f'"{path}" -v'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding=tm.sys_encoding(),
            timeout=10,
        )
        # Under windows, the output is on stderr
        data = result.stdout or result.stderr
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as e:
        data = ""
    try:
        vers = ((data.split(" "))[1]).split(".")
        if len(vers) != 3:
            vers = (0, 0, 0)
    except:
        vers = (0, 0, 0)
    return tuple(vers)


def _is_lua51(lua_bin):
    res = False
    v = _lua_version(lua_bin)
    if (v[0] == "5") and (v[1] >= "1"):
        res = True
    return res


def _sys_lua_bin():
    sys_lua_bin = tm.gd("_sys_lua_bin", "")
    if sys_lua_bin != "":
        return sys_lua_bin

    cur_os = tm.OS()
    if cur_os == "Windows":
        func = sys_app_path_win
    else:
        func = sys_app_path_lin

    sys_lua_bin = func("lua")
    if (sys_lua_bin != "") and not _is_lua51(sys_lua_bin):
        tm.print_debug(f"'{sys_lua_bin}' not a lua 5.1 min.")
        sys_lua_bin = ""

    tm.print_debug(f"lua bin is: '{sys_lua_bin}'.")
    tm.setgd("_sys_lua_bin", sys_lua_bin)
    return sys_lua_bin


def _is_lua_interpreter(path: str, timeout=2) -> bool:
    """
    Checks if the given path points to a valid Lua interpreter.

    Args:
        path (str): Path to the executable to check.
        timeout (int, optional): Timeout for the subprocess in seconds. Defaults to 2.

    Returns:
        bool: True if the path is a Lua interpreter, False otherwise.
    """
    try:
        result = subprocess.run(
            [path, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return (result.returncode == 0) and (
            (result.stdout.startswith("Lua") or result.stderr.startswith("Lua"))
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False


class LuaProcessBase:
    CUST_ENV = {
        "PATH": {"replace": False},
        "LUA_PATH": {"replace": True},
        "LUA_CPATH": {"replace": True},
    }

    def __init__(self, lua_bin="", request_handler=None, timeout=10):
        """
        Initializes the Lua function execution engine.

        Args:
            lua_bin (str, optional): Path to the Lua interpreter. Defaults to system path.
            request_handler: Handler for JSON-RPC requests.
            timeout (int, optional): Timeout for operations in seconds. Defaults to 10.

        Raises:
            ETUMRuntimeError: If the Lua path is invalid or no interpreter is found.
        """
        if lua_bin != "":
            if shutil.which(lua_bin) is None:
                raise ETUMRuntimeError(
                    f"The passed lua path is not pointing to an executable: '{lua_bin}'"
                )

            if not _is_lua_interpreter(lua_bin):
                raise ETUMRuntimeError(
                    f"The passed executable is not a lua interpreter: '{lua_bin}'"
                )
        else:
            lua_bin = _sys_lua_bin()
            if lua_bin == "":
                raise ETUMRuntimeError(f"No valid lua interpreter found")
            tm.setgd("lua_bin", lua_bin)

        self._lbin = lua_bin
        self._req_handler = request_handler
        self._process = None
        self._port = 0
        self._timeout = timeout
        self._rpc = None

    def start(self):
        """
        Starts the Lua subprocess for function execution.

        Sets up environment variables, binds a socket for communication,
        and initializes the JSON-RPC client.

        Raises:
            ETUMRuntimeError: If the subprocess is already started.
        """
        # This thread is not closed until new test is loaded
        if self._process is not None:
            raise ETUMRuntimeError("The function subprocess has already been started.")

        func_proc_path = os.path.realpath(
            os.path.join(subproc_path(), "lua_func")
        )

        # POpen config
        CUST_ENV = {
            "PATH": {"replace": False},
            "LUA_PATH": {"replace": True},
            "LUA_CPATH": {"replace": True},
        }

        lua_env = tm.gd("lua_env", {})
        env = os.environ.copy()
        if not isinstance(lua_env, dict):
            raise ETUMRuntimeError(f"The 'lua_env' global value should be a dictionary. But it is '{lua_env}'.")

        for k, v in CUST_ENV.items():
            e = lua_env.get(k, "")
            if e != "":
                if v["replace"]:
                    env[k] = e
                else:
                    env[k] = e + ";" + env.get(k, "")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        self._port = sock.getsockname()[1]
        sock.close()

        # POpen params
        params = [
            self._lbin,
            "main.lua",
            "--timeout",
            f"{self._timeout}",
            "--host",
            "127.0.0.1",
            "--port",
            f"{self._port}",
        ]

        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            params.append("--verbose")

        self._process = subprocess.Popen(params, env=env, cwd=func_proc_path)

        self._rpc = JsonRpcClient(
            "localhost", self._port, req_handler=self._req_handler
        )
        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            self._rpc.dbg_out = sys.stdout
        self._rpc.start()

    def join(self):
        """
        Joins the RPC thread and resets the process state.
        """
        if self._rpc is not None:
            self._rpc.join()
            self._rpc = None
        self._process = None

    def wait_ready(self, timeout=None):
        """
        Waits for the RPC client to be ready.

        Args:
            timeout (float, optional): Timeout in seconds. Defaults to None.

        Returns:
            bool: True if ready, False otherwise.
        """
        if self._rpc is not None and self._rpc.is_alive():
            return self._rpc.wait_ready(timeout)
        return False

    def is_alive(self):
        if self._rpc is not None:
            return self._rpc.is_alive()
        return False

    def stop(self):
        """
        Stops the RPC client.
        """
        if self._rpc is not None:
            self._rpc.stop()

