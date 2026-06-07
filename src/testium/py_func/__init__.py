#!/usr/bin/env python
import sys
import multiprocessing
from py_func.tm import _init_api, _remote_print
from runtime.stdout_redirect import stdio_redir
from runtime.jrpc import RPC_PORT_SENTINEL


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
    parser.add_argument("-p", "--port", type=int, help="port to listen to (0 = OS-assigned)",
                        default=0)
    parser.add_argument("-t", "--timeout", type=float, help="Timeout waiting for connection",
                        default=10)
    parser.add_argument("-v", "--verbose", action='store_true', help="port to listen to")
    args = parser.parse_args()

    thrd_api = _init_api(args.ip, args.port, args.timeout)
    # debug the server
    if args.verbose:
        thrd_api.dbg_out = stdio_redir.ini_stdout
    thrd_api.start()

    # Announce the actual bound port on real stdout (before redirection) so the
    # parent connects only once we are listening.
    port = thrd_api.wait_bound(args.timeout)
    if port is None:
        print("py_func: failed to bind a listening port", file=sys.stderr, flush=True)
        return
    print(f"{RPC_PORT_SENTINEL}{port}", flush=True)

    # redirect I/O
    outstream = TcpStdOut()
    stdio_redir.redirect(outstream)
    try:
        while thrd_api.is_alive():
            thrd_api.join(1)
    finally:
        stdio_redir.restore()