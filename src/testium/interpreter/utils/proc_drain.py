"""Drain a subprocess stdout/stderr into testium's print pipeline.

Captured lines go through the parent's stdio_redir, so they reach the
test log AND the live output (terminal in batch mode, GUI text panel
in -r mode). This is essential for diagnosing early-startup errors
of py_func / lua_func subprocesses (missing modules, unhandled
exceptions before the in-process redirection kicks in, lua
``require`` failures, anything written to fd 1/2 directly).
"""
import threading


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
