import os
import shutil
import sys
import subprocess
import socket
from runtime.jrpc import JsonRpcClient
import api.testium as tm
from interpreter.utils.paths import sys_app_path_lin, sys_app_path_win
from runtime.tum_except import ETUMRuntimeError
from interpreter.utils.paths import testium_path, subproc_path


def _python_version(path: str):
    cmd = f'"{path}" -c "import sys; print(sys.version_info[:3])"'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding=tm.sys_encoding(),
            timeout=10,
        )
        data = result.stdout
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as e:
        tm.print_debug(str(e))
        data = ""
    return eval(data)


def _is_python3(python_bin):
    try:
        v = _python_version(python_bin)
        if v[0] == 3:
            res = True
    except:
        res = False

    return res


def _is_python_interpreter(path: str, timeout=2) -> bool:
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


def _sys_python_bin():
    sys_python_bin = ""

    cur_os = tm.OS()
    if cur_os == "Windows":
        func = sys_app_path_win
    else:
        func = sys_app_path_lin

    exe = ["python3", "python"]
    for e in exe:
        sys_python_bin = func(e)
        if sys_python_bin == "":
            continue
        if _is_python3(sys_python_bin):
            break
        sys_python_bin = ""

    return sys_python_bin


class PyProcessBase:
    CUST_ENV = {
        "PATH": {"replace": False},
        "PYTHONPATH": {"replace": True},
    }

    def __init__(self, python_bin="", request_handler=None, timeout=10, python_path=""):
        self._pbin = python_bin
        if (self._pbin is not None) and (self._pbin != ""):

            if shutil.which(self._pbin) is None:
                raise ETUMRuntimeError(
                    f"The passed python path is not pointing to an executable: '{self._pbin}'"
                )

            if not _is_python_interpreter(self._pbin):
                raise ETUMRuntimeError(
                    f"The passed executable is not a python interpreter: '{self._pbin}'"
                )

        else:
            self._pbin = tm.gd("_cached_python_bin", "")
            if self._pbin == "":
                self._pbin = _sys_python_bin()
                tm.setgd("_cached_python_bin", self._pbin)

            if self._pbin == "":
                raise ETUMRuntimeError(f"No valid python interpreter found")

        self._ppath = python_path
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

        # POpen config
        py_env = tm.gd("python_env", {})
        if not isinstance(py_env, dict):
            raise ETUMRuntimeError(f"The 'py_env' global value should be a dictionary. But it is '{py_env}'.")

        env = os.environ.copy()
        for k, v in self.CUST_ENV.items():
            e = py_env.get(k, "")
            if e != "":
                if v["replace"]:
                    env[k] = e
                else:
                    env[k] = e + os.pathsep + env.get(k, "")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        self._port = sock.getsockname()[1]
        # Port was reserved until the sub-process is started. Now released.
        if sock is not None:
            sock.close()

        # Add the path of the subprocess (root sources of testium)
        tstium_path = os.path.realpath(testium_path())
        func_proc_path = os.path.realpath(subproc_path())
        env["PYTHONPATH"] = tstium_path + os.pathsep + self._ppath + os.pathsep + env.get("PYTHONPATH", "")

        params = [
            self._pbin,
            # "-m",
            "py_func",
            "-p",
            f"{self._port}",
            "-t",
            f"{self._timeout}",
        ]

        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            params.append("-v")

        self._process = subprocess.Popen(
            params, env=env, cwd=func_proc_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            restore_signals=False,
        )

        self._rpc = JsonRpcClient(
            "localhost", self._port, req_handler=self._req_handler
        )
        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            self._rpc.dbg_out = sys.stdout
        self._rpc.start()

    @property
    def python_bin(self):
        return self._pbin


    def join(self):
        if self._rpc is not None:
            self._rpc.join()
            self._rpc = None
        self._process = None

    def wait_ready(self, timeout=None):
        if self._rpc is not None and self._rpc.is_alive():
            return self._rpc.wait_ready(timeout)
        return False

    def is_alive(self):
        if self._rpc is not None:
            return self._rpc.is_alive()
        return False

    def stop(self):
        if self._rpc is not None:
            self._rpc.stop()
