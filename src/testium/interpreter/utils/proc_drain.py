"""Drain a subprocess stdout/stderr into testium's print pipeline.

Captured lines go through the parent's stdio_redir, so they reach the
test log AND the live output (terminal in batch mode, GUI text panel
in -r mode). This is essential for diagnosing early-startup errors
of py_func / lua_func subprocesses (missing modules, unhandled
exceptions before the in-process redirection kicks in, lua
``require`` failures, anything written to fd 1/2 directly).
"""
import threading
from time import monotonic

from runtime.jrpc import RPC_PORT_SENTINEL


def _drain_pipe(pipe, prefix):
    try:
        for raw in iter(pipe.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                continue
            if prefix:
                print(f"{prefix}{line}")
            else:
                print(line)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def drain_to_log(process, prefix=""):
    """Spawn daemon threads that read ``process.stdout`` and
    ``process.stderr`` line by line and print each line through the
    parent's stdout (so it reaches the log + live output).

    Each thread exits cleanly when the subprocess closes the
    corresponding pipe (i.e. when it exits). Daemon flag ensures they
    do not block testium exit.
    """
    threads = []
    for pipe in (process.stdout, process.stderr):
        if pipe is None:
            continue
        t = threading.Thread(
            target=_drain_pipe, args=(pipe, prefix), daemon=True,
        )
        t.start()
        threads.append(t)
    return threads


def drain_and_read_port(process, prefix=""):
    """Like :func:`drain_to_log`, but the stdout reader also watches for the
    startup port sentinel. Returns a ``holder`` dict (passed to
    :func:`wait_for_port`); all non-sentinel lines are still forwarded to the
    log. stderr is drained as usual.
    """
    holder = {"port": None, "evt": threading.Event()}

    def _read_stdout(pipe):
        try:
            for raw in iter(pipe.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if holder["port"] is None and line.startswith(RPC_PORT_SENTINEL):
                    try:
                        holder["port"] = int(line[len(RPC_PORT_SENTINEL):].strip())
                    except ValueError:
                        continue
                    holder["evt"].set()
                    continue
                if line:
                    print(f"{prefix}{line}" if prefix else line)
        finally:
            try:
                pipe.close()
            except Exception:
                pass
            # Unblock the waiter on EOF even if the sentinel never came.
            holder["evt"].set()

    if process.stdout is not None:
        threading.Thread(
            target=_read_stdout, args=(process.stdout,), daemon=True,
        ).start()
    if process.stderr is not None:
        threading.Thread(
            target=_drain_pipe, args=(process.stderr, prefix), daemon=True,
        ).start()
    return holder


def wait_for_port(process, holder, deadline):
    """Block until the port sentinel arrives, the process dies, or *deadline*
    seconds elapse. Returns the port int or ``None``.
    """
    end = monotonic() + deadline
    while holder["port"] is None:
        remaining = end - monotonic()
        if remaining <= 0:
            break
        holder["evt"].wait(min(remaining, 0.2))
        if holder["port"] is not None:
            break
        if process.poll() is not None:
            # Child exited; give the reader a moment to flush a trailing line.
            holder["evt"].wait(0.2)
            break
    return holder["port"]
