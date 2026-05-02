#!/usr/bin/env python
import multiprocessing
from py_func.tm import _init_api, _remote_print
from runtime.stdout_redirect import stdio_redir


class TcpStdOut:
    def __init__(self):
        pass

    def write(self, s: str) -> None:
        _remote_print(s)

    def flush(self):
        pass


def main():
    # This line sets the method for the "Process" function. It is required for Linux
    # support of the test dialogs.
    multiprocessing.set_start_method('spawn')

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ip", type=str, help="Ip address or hostname to listen to",
                        default="localhost")
    parser.add_argument("-p", "--port", type=int, help="port to listen to",
                        default=9000)
    parser.add_argument("-t", "--timeout", type=float, help="Timeout waiting for connection",
                        default=10)
    parser.add_argument("-v", "--verbose", action='store_true', help="port to listen to")
    args = parser.parse_args()

    thrd_api = _init_api(args.ip, args.port, args.timeout)
    # redirect I/O
    outstream = TcpStdOut()
    stdio_redir.redirect(outstream)
    # debug the server
    if args.verbose:
        thrd_api.dbg_out = stdio_redir.ini_stdout
    thrd_api.start()
    try:
        while thrd_api.is_alive():
            thrd_api.join(1)
    finally:
        stdio_redir.restore()