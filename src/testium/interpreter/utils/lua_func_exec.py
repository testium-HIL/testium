import os
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
    global function_call_process
    function_call_process = LuaFuncExecEngine(lua_path, request_handler, timeout)
    return function_call_process


def is_lua_interpreter(path: str, timeout=2) -> bool:
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

    def __init__(self, lua_path="", request_handler=None, timeout=10):
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
        run the subprocess to execute the python functions of the test.
        """
        # This thread is not closed until new test is loaded
        if self._process is not None:
            raise ETUMRuntimeError("The function subprocess has already been started.")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        self._port = sock.getsockname()[1]

        func_proc_path = os.path.join(tm.gd("testium_path"),"lua_func")
        lua_env = tm.gd("lua_env", {})
        tm.print_debug(f"lua_env : {lua_env}")

        params = [self._lpath, "main.lua", "--timeout", f"{self._timeout}", "--host", "127.0.0.1", "--port", f"{self._port}"]

        if tm.debug_enabled():
            params.append("--verbose")

        self._process = subprocess.Popen(
            params, env=lua_env, cwd=func_proc_path
        )

        # Port was reserved until the sub-process is started. Now released.
        if sock is not None:
            sock.close()

        self._rpc = JsonRpcClient("localhost", self._port, req_handler=self._req_handler)
        self._rpc.start()

    def join(self):
        if self._rpc is not None:
            self._rpc.join()
            self._rpc = None
        self._process = None

    def wait_ready(self, timeout=None):
        if self._rpc is not None and self._rpc.is_alive():
            return self._rpc.wait_ready(timeout)
        return False

    def stop(self):
        if self._rpc is not None:
            self._rpc.stop()

    def func_call(self, file: str, func_name: str, params: list, verbose: bool = True):
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
    """Executes a python function and returns its result and reported values"""
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