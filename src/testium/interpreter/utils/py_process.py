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

        # In Flatpak the host can't see /app/lib/testium, so use a staged copy
        # under /tmp (shared between sandbox and host) for both cwd and as the
        # root in PYTHONPATH. Outside Flatpak the original paths are used.
        if bins._in_flatpak():
            tstium_path = bins._get_host_testium_path()
            func_proc_path = tstium_path
        else:
            tstium_path = os.path.realpath(testium_path())
            func_proc_path = os.path.realpath(subproc_path())
        env["PYTHONPATH"] = tstium_path + os.pathsep + self._ppath + os.pathsep + env.get("PYTHONPATH", "")

        cmd_args = [
            "py_func",
            "-p",
            f"{self._port}",
            "-t",
            f"{self._timeout}",
        ]

        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            cmd_args.append("-v")

        if bins._in_flatpak():
            # Run on the host outside the sandbox: avoids glibc ABI mismatches
            # between the Flatpak runtime and host shared libraries.
            host_env = {
                k: env[k] for k in ("PYTHONPATH", "PATH")
                if k in env and env[k]
            }
            params = bins.flatpak_host_spawn(
                self._pbin, cmd_args, host_cwd=func_proc_path,
                extra_env=host_env,
            )
            popen_kwargs = {}
        else:
            params = [self._pbin, *cmd_args]
            popen_kwargs = {"env": env, "cwd": func_proc_path}

        self._process = subprocess.Popen(
            params,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            restore_signals=False,
            **popen_kwargs,
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
        # Force-kill the worker if it's still running. Needed when user code
        # in the worker is stuck (e.g. sleep, blocking I/O) and won't notice
        # the parent closing the RPC socket on its own.
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                pass
