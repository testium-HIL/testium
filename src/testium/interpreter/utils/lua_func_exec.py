import os
import sys
import shutil
import subprocess
import socket
import libs.testium as tm
from interpreter.utils.paths import sys_app_path_lin, sys_app_path_win
from interpreter.utils.tum_except import ETUMRuntimeError
from interpreter.utils.jrpc import JsonRpcClient
from interpreter.test_items.test_result import TestValue

function_call_process = None

def _lua_version(path: str):
    cmd = f'"{path}" -v'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding=tm.sys_encoding(),
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

    tm.setgd("_sys_lua_bin", sys_lua_bin)
    return sys_lua_bin



def lua_func_call_init(lua_bin, request_handler, timeout):
    """
    Initializes the global Lua function execution process.

    Args:
        lua_bin (str): Path to the Lua interpreter executable. If empty, uses system default.
        request_handler: Handler for JSON-RPC requests.
        timeout (int): Timeout for operations in seconds.

    Returns:
        LuaFuncExecEngine: The initialized engine instance.

    Raises:
        ETUMRuntimeError: If the Lua path is invalid or no interpreter is found.
    """
    global function_call_process
    function_call_process = LuaFuncExecEngine(lua_bin, request_handler, timeout)
    return function_call_process


def is_lua_interpreter(path: str, timeout=2) -> bool:
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
        return (result.returncode == 0) and (result.stdout.startswith("Lua"))
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False


class LuaFuncExecEngine:
    """
    Engine for executing Lua functions via a subprocess and JSON-RPC communication.

    This class manages a Lua interpreter subprocess, handles RPC communication,
    and executes specified functions with parameters.
    """

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

            if not is_lua_interpreter(lua_bin):
                raise ETUMRuntimeError(
                    f"The passed executable is not a lua interpreter: '{lua_bin}'"
                )
        else:
            lua_bin = _sys_lua_bin()
            if lua_bin == "":
                raise ETUMRuntimeError(
                    f"No valid lua interpreter found"
                )
            tm.setgd("lua_bin", lua_bin)

        self._lpath = lua_bin
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

        func_proc_path = os.path.join(tm.gd("testium_path"),"lua_func")

        # POpen config
        CUST_ENV = {
            "PATH": {"replace": False},
            "LUA_PATH": {"replace": True},
            "LUA_CPATH": {"replace": True},
        }

        lua_env = tm.gd("lua_env", {})
        env = os.environ.copy()
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

        # POpen params
        params = [self._lpath, "main.lua", "--timeout", f"{self._timeout}", "--host", "127.0.0.1", "--port", f"{self._port}"]

        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            params.append("--verbose")

        self._process = subprocess.Popen(
            params, env=env, cwd=func_proc_path
        )

        # Port was reserved until the sub-process is started. Now released.
        if sock is not None:
            sock.close()

        self._rpc = JsonRpcClient("localhost", self._port, req_handler=self._req_handler)
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

    def stop(self):
        """
        Stops the RPC client.
        """
        if self._rpc is not None:
            self._rpc.stop()

    def func_call(self, file: str, func_name: str, params: list, verbose: bool = True):
        """
        Calls a Lua function via RPC and returns the result.

        Args:
            file (str): Path to the Lua file containing the function.
            func_name (str): Name of the function to call.
            params (list): List of parameters to pass to the function.
            verbose (bool, optional): Whether to enable verbose output. Defaults to True.

        Returns:
            tuple: (TestValue.SUCCESS, (result, reported_values)) on success,
                   (TestValue.FAILURE, error_message) on failure.

        Raises:
            ETUMRuntimeError: If the RPC call fails or no process is active.
        """
        if (self._rpc is not None) and self._rpc.is_alive():
            answer = self._rpc.call(
                "func_call",
                {
                    "file": file,
                    "fname": func_name,
                    "params": params,
                    "verbose": verbose,
                },
            )
            if "result" in answer:
                reported_values = answer["result"].get("reported_values", {})
                if "returned_value" in answer["result"]:
                    res = answer["result"]["returned_value"]
                    return TestValue.SUCCESS, (res, reported_values)
                else:
                    raise ETUMRuntimeError(
                        "Unexepected py_func jrpc result. To be reported to testium support team."
                    )

            # In case an error was encountered in the called function
            elif "error" in answer:
                msg = f"{answer["error"]}"
                return TestValue.FAILURE, msg

            else:
                raise ETUMRuntimeError(
                    "Unexepected py_func call failure to be reported to testium support team."
                )
        else:
            raise ETUMRuntimeError(
                "No function execution process active. To be reported to testium support team."
            )


def lua_func_exec(file: str, func_name: str, params: list, verbose: bool = True):
    """
    Executes a Lua function using the global function call process.

    Args:
        file (str): Path to the Lua file containing the function.
        func_name (str): Name of the function to call.
        params (list): List of parameters to pass to the function.
        verbose (bool, optional): Whether to enable verbose output. Defaults to True.

    Returns:
        tuple: (success_status, result_or_error) where success_status is TestValue.SUCCESS or FAILURE.

    Raises:
        ETUMRuntimeError: If no function execution process is active.
    """
    global function_call_process

    if function_call_process is not None:
        success, result = function_call_process.func_call(
            file, func_name, params, verbose
        )
    else:
        raise ETUMRuntimeError(
            "No function execution process active. To be reported to testium support team."
        )

    return success, result