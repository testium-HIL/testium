import os
import sys
import subprocess

import api.testium as tm
from runtime.jrpc import JsonRpcClient
from interpreter.utils.paths import subproc_path, no_window_kwargs
from runtime.tum_except import ETUMRuntimeError
from interpreter.utils import bins
from interpreter.utils.proc_drain import drain_and_read_port, wait_for_port


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

        # In Flatpak the host can't see /app/lib/testium/lua_func, so use a
        # staged copy under /tmp (shared between sandbox and host).
        if bins._in_flatpak():
            func_proc_path = os.path.join(
                bins._get_host_testium_path(), "lua_func"
            )
        else:
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

        # POpen params (port 0 -> the Lua server picks a free port and reports it)
        cmd_args = [
            "main.lua",
            "--timeout",
            f"{self._timeout}",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
        ]

        if tm.debug_enabled() and tm.gd("debug_rpc", False):
            cmd_args.append("--verbose")

        if bins._in_flatpak():
            # Run on the host outside the sandbox: avoids glibc ABI mismatches
            # between the Flatpak runtime and host shared libraries.
            host_env = {
                k: env[k] for k in ("LUA_PATH", "LUA_CPATH", "PATH")
                if k in env and env[k]
            }
            params = bins.flatpak_host_spawn(
                self._lbin, cmd_args, host_cwd=func_proc_path,
                extra_env=host_env,
            )
            popen_kwargs = {}
        else:
            params = [self._lbin, *cmd_args]
            popen_kwargs = {"env": env, "cwd": func_proc_path}

        self._process = subprocess.Popen(
            params,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            restore_signals=False,
            **no_window_kwargs(),
            **popen_kwargs,
        )
        # Forward subprocess output to the log and read the startup port sentinel.
        holder = drain_and_read_port(self._process, prefix="[lua_func] ")
        self._port = wait_for_port(
            self._process, holder, tm.gd("proc_start_timeout", 30)
        )
        if self._port is None:
            # Worker died before announcing its port: reset so a later start() retries clean.
            self.stop()
            self.join()
            return

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

