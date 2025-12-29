#!/usr/bin/env python
import multiprocessing
from py_func.tm import _init_api, remote_print
from interpreter.utils.stdout_redirect import stdio_redir


class TcpStdOut:
    def __init__(self):
        pass

    def write(self, s: str) -> None:
        remote_print(s)

    def flush(self):
        pass


def main():
    # This line sets the method for the "Process" function. It is required for Linux
    # support of the test dialogs.
    multiprocessing.set_start_method('spawn')

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, help="port to listen to",
                        default="/etc/jsonrpc-echo.conf")
    args = parser.parse_args()

    thrd_api = _init_api(args.port)
    outstream = TcpStdOut()
    stdio_redir.redirect(outstream)
    # debug the server
    # thrd_api.dbg_out = stdio_redir.ini_stdout
    try:
        while thrd_api.is_alive():
            thrd_api.join(1)
    finally:
        stdio_redir.restore()