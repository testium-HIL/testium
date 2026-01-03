import os
import sys
import shutil
import subprocess
import socket
import libs.testium as tm
from interpreter.utils.paths import sys_lua_path
from interpreter.utils.tum_except import ETUMRuntimeError
from interpreter.utils.jrpc import JsonRpcClient
from interpreter.test_items.test_result import TestValue

function_call_process = None


def lua_func_call_init(lua_path, request_handler, timeout):
    """
    Initializes the global Lua function execution process.

    Args:
        lua_path (str): Path to the Lua interpreter executable. If empty, uses system default.
        request_handler: Handler for JSON-RPC requests.
        timeout (int): Timeout for operations in seconds.

    Returns:
        LuaFuncExecEngine: The initialized engine instance.

    Raises:
        ETUMRuntimeError: If the Lua path is invalid or no interpreter is found.
    """
    global function_call_process
    function_call_process = LuaFuncExecEngine(lua_path, request_handler, timeout)
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

    def __init__(self, lua_path="", request_handler=None, timeout=10):
        """
        Initializes the Lua function execution engine.

        Args:
            lua_path (str, optional): Path to the Lua interpreter. Defaults to system path.
            request_handler: Handler for JSON-RPC requests.
            timeout (int, optional): Timeout for operations in seconds. Defaults to 10.

        Raises:
            ETUMRuntimeError: If the Lua path is invalid or no interpreter is found.
        """
        if lua_path != "":
            if shutil.which(lua_path) is None:
                raise ETUMRuntimeError(
                    f"The passed lua path is not pointing to an executable: '{lua_path}'"
                )

            if not is_lua_interpreter(lua_path):
                raise ETUMRuntimeError(
                    f"The passed executable is not a lua interpreter: '{lua_path}'"
                )
        else:
            lua_path = sys_lua_path()
            if lua_path == "":
                raise ETUMRuntimeError(
                    f"No valid lua interpreter found"
                )
            tm.setgd("lua_path", lua_path)

        self._lpath = lua_path
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