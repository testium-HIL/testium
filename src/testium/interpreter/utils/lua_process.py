import os
import sys
import subprocess
import socket

import api.testium as tm
from runtime.jrpc import JsonRpcClient
from interpreter.utils.paths import subproc_path
from runtime.tum_except import ETUMRuntimeError
from interpreter.utils import bins
from interpreter.utils.proc_drain import drain_to_log


class LuaProcessBase:
    CUST_ENV = {
        "PATH": {"replace": False},
        "LUA_PATH": {"replace": True},
        "LUA_CPATH": {"replace": True},
    }

    def __init__(self, request_handler=None, timeout=10):
        """Initializes the Lua function execution engine.

        Raises:
            ETUMRuntimeError: If no Lua >= 5.1 interpreter is found.
        """
        self._lbin = bins.lua_bin()
        if not self._lbin:
            raise ETUMRuntimeError("No valid Lua 5.1+ interpreter found")
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
        bins.apply_host_libs(env)
        if not isinstance(lua_env, dict):
            raise ETUMRuntimeError(f"The 'lua_env' global value should be a dictionary. But it is '{lua_env}'.")

        for k, v in CUST_ENV.items():
            e = lua_env.get(k, "")
            if e != "":
                if v["replace"]:
                    env[k] = e
                else:
                    env[k] = e + ";" + env.get(k, "")
        bins.apply_host_lua_paths(env)

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

        self._process = subprocess.Popen(
            params, env=env, cwd=func_proc_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            restore_signals=False,
        )
        # Route subprocess stdout/stderr (lua require failures, syntax
        # errors, anything written to fd 1/2 before the in-script
        # remote_print is set up) into the parent's log.
        drain_to_log(self._process, prefix="[lua_func] ")

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
        # Force-kill the worker if it's still running. Needed when user code
        # in the worker is stuck and won't notice the parent closing the RPC
        # socket on its own.
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                pass

