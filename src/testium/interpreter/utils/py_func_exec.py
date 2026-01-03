import sys
import shutil
import subprocess
import socket
import libs.testium as tm
from interpreter.utils.paths import sys_python_path
from interpreter.utils.tum_except import ETUMRuntimeError
from interpreter.utils.jrpc import JsonRpcClient
from interpreter.test_items.test_result import TestValue

function_call_process = None


def py_func_call_init(python_path, request_handler):
    global function_call_process
    function_call_process = PyFuncExecEngine(python_path, request_handler)
    return function_call_process


def is_python_interpreter(path: str, timeout=2) -> bool:
    try:
        result = subprocess.run(
            [path, "-c", "import sys; print(sys.executable)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False


class PyFuncExecEngine:

    def __init__(self, python_path="", request_handler=None):
        if python_path != "":

            if shutil.which(python_path) is None:
                raise ETUMRuntimeError(
                    f"The passed python path is not pointing to an executable: '{python_path}'"
                )

            if not is_python_interpreter(python_path):
                raise ETUMRuntimeError(
                    f"The passed executable is not a python interpreter: '{python_path}'"
                )

        else:
            python_path = sys_python_path()
            if python_path == "":
                raise ETUMRuntimeError(
                    f"No valid python interpreter found"
                )
            tm.setgd("python_path", python_path)

        self._ppath = python_path
        self._req_handler = request_handler
        self._process = None
        self._port = 0
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

        func_proc_path = tm.gd("testium_path")

        params = [self._ppath, "-m", "py_func", "-p", f"{self._port}"]
        if tm.debug_enabled():
            params.append("-v")

        self._process = subprocess.Popen(
            params, cwd=func_proc_path
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


def py_func_exec(file: str, func_name: str, params: list, verbose: bool = True):
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
