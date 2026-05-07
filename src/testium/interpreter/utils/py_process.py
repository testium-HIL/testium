import os
import sys
import subprocess
import socket
from runtime.jrpc import JsonRpcClient
import api.testium as tm
from runtime.tum_except import ETUMRuntimeError
from interpreter.utils.paths import testium_path, subproc_path
from interpreter.utils import bins
from interpreter.utils.proc_drain import drain_to_log


class PyProcessBase:
    CUST_ENV = {
        "PATH": {"replace": False},
        "PYTHONPATH": {"replace": True},
    }

    def __init__(self, request_handler=None, timeout=10, python_path=""):
        self._pbin = bins.python_bin()
        if not self._pbin:
            raise ETUMRuntimeError("No valid Python 3 interpreter found")
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
        bins.apply_host_libs(env)
        # PYTHONUSERBASE is set by the Flatpak runtime to isolate sandbox
        # user packages; remove it so the host Python finds ~/.local packages.
        env.pop("PYTHONUSERBASE", None)
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            restore_signals=False,
        )
        # Route subprocess stdout/stderr (early-startup errors,
        # unhandled exceptions, anything written to fd 1/2 before the
        # in-process JSON-RPC stdio_redir kicks in) into the parent's
        # log.
        drain_to_log(self._process, prefix="[py_func] ")

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
