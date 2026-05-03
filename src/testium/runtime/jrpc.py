import socket
import json
from time import monotonic
import threading
import itertools
from time import sleep
from typing import Callable, Any
try:
    import api.testium as tm
except:
    import py_func.tm as tm

from runtime.tum_except import ETUMRuntimeError

"""Lightweight JSON-RPC 2.0 helpers over TCP sockets.

This module implements a minimal JSON-RPC 2.0 messaging layer using
newline-delimited JSON over TCP sockets. It is intended for simple
request/response exchanges useful during development and testing. The
implementation favors clarity and small surface area rather than full
JSON-RPC compliance.

Main public classes
- `JsonRpcConnection` -- Wraps a connected TCP socket and manages
    sending requests and dispatching incoming requests and responses. It
    runs a background receiver thread and pairs outgoing requests with
    responses using per-request identifiers and `threading.Event` objects.

- `JsonRpcBase` -- Threaded base class for simple server/client helpers.
    Provides a `call()` method to send requests to the connected peer and
    a `handle_request()` hook that can be overridden or supplied at
    construction.

- `JsonRpcSrv` / `JsonRpcClient` -- Convenience single-connection server
    and client classes that accept/connect to a peer and create a
    `JsonRpcConnection` to handle message I/O.

Usage example (server):

        srv = JsonRpcSrv(port, req_handler=my_handler)
        srv.start()  # runs in background thread

Usage example (client):

        clt = JsonRpcClient(host, port)
        clt.start()
        result = clt.call('method_name', {'foo': 'bar'})

Notes:
- Messages must be valid JSON objects and are expected to be
    single-line (newline-delimited).
- This helper is intended for local/testing use; it does not provide
    authentication, encryption, or advanced JSON-RPC features (notifications,
    batch requests, error objects beyond simple dicts).
"""


class JsonRpcConnection:

    def __init__(
        self,
        name,
        conn: socket.socket,
        req_handler: Callable[..., Any],
        dbg_out=None,
    ):
        self.name = name
        self.conn = conn
        if not callable(req_handler):
            raise TypeError("req_handler must be a callable (function)")

        # User-provided function called to handle incoming requests.
        # It may accept either the full request dict or (method, params).
        self.req_handler = req_handler
        self.send_lock = threading.Lock()
        self.pending = {}  # id -> Event + response
        self.id_gen = itertools.count(1)
        self.running = True
        self._dbg_out = dbg_out
        self._event_ready = threading.Event()

        self.conn.settimeout(0.1)

        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()

    @property
    def dbg_out(self):
        return self._dbg_out

    @dbg_out.setter
    def dbg_out(self, dbg_out):
        self._dbg_out = dbg_out

    # ---------- Reception ----------
    def _recv_loop(self):
        buffer = b""

        try:
            self._event_ready.set()
            while self.running:
                try:
                    data = self.conn.recv(4096)
                    if not data:
                        self.print_info("Connection closed")
                        break
                except socket.timeout:
                    continue
                else:
                    buffer += data

                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        try:
                            msg = json.loads(line.decode())
                        except Exception as e:
                            self.print_info(str(e))
                        else:
                            if isinstance(msg, dict):
                                self._dispatch(msg)
                            else:
                                self.print_info(f"msg not dict ! = '{msg}'")

        except (ConnectionResetError, OSError):
            self.print_info("Connection lost")

        finally:
            self.running = False

    # ---------- Dispatch ----------
    def _dispatch(self, msg):
        if "method" in msg:
            # request to be sent
            meth = msg["method"]
            params = msg.get("params", None)
            rid = msg.get("id", None)

            threading.Thread(
                target=self._handle_request, args=(meth, params, rid), daemon=True
            ).start()

        elif "id" in msg:
            # we just received an answer to a previously sent request
            if msg["id"] in self.pending:
                self.pending[msg["id"]]["response"] = msg
                self.pending[msg["id"]]["event"].set()
            else:
                self.print_info(f"msg id '{msg['id']}' inconsistency")

    # ---------- Handler ----------
    def _handle_request(self, meth, params, rid=None):
        """Basic request handler.

        In this implementation
        a `req_handler` callable provided at construction is invoked to handle
        the request and produce a response value.
        """
        # print(f"Request received: m:'{meth}', p:'{params}'")

        # Delegate handling to the user-provided function. Accept both
        # `handler(req_dict)` and `handler(method, params)` signatures; if
        # the handler raises, capture the exception message as the result.
        try:
            result = self.req_handler(meth, params)
        except Exception as exc:
            result = {"error": str(exc)}

        self.print_info(f"result: {result}")

        # If the request contains an `id`, send a JSON-RPC response.
        if rid is not None:
            msg = {"jsonrpc": "2.0", **result, "id": rid}
            self._send(msg)

    # ---------- Send ----------
    def _send(self, obj):
        """Send a JSON-serializable object terminated by newline.

        The send operation is protected by a lock to avoid interleaving when
        multiple threads attempt to write to the underlying socket.
        """
        msg = json.dumps(obj) + "\n"
        data = (msg).encode()
        self.print_info(f"sending : " + msg)
        with self.send_lock:
            self.conn.sendall(data)

    # ---------- Outgoing request ----------
    def call(self, method, params=None, timeout=3600.0):
        """Send a request and wait for its response.

        Args:
            method: The RPC method name.
            params: Parameters for the method (any JSON-serializable object).
            timeout: Seconds to wait for a response before raising
                `TimeoutError`.

        Returns:
            The response message (dict) received from the peer.

        Raises:
            TimeoutError: If no response is received within `timeout`.
        """

        req_id = next(self.id_gen)
        event = threading.Event()

        self.pending[req_id] = {"event": event, "response": None}

        self._send({"jsonrpc": "2.0", "method": method, "params": params, "id": req_id})

        if not event.wait(timeout):
            # Timeout: remove pending entry and raise
            self.pending.pop(req_id, None)
            raise TimeoutError("Timeout JSON-RPC")

        return self.pending.pop(req_id)["response"]

    def print_info(self, msg):
        if self.dbg_out is not None:
            print(f"{self.name}: " + str(msg), file=self.dbg_out)

    def stop(self):
        if self.running:
            self.running = False

    def join(self):
        self.recv_thread.join()

    def is_alive(self):
        return self.recv_thread.is_alive()

    def wait_ready(self, timeout=None):
        return self._event_ready.wait(timeout)


class JsonRpcBase(threading.Thread):
    """Threaded base class for simple JSON-RPC server/client helpers.

    Subclasses implement `run()` to accept or establish a single TCP
    connection and create a `JsonRpcConnection` instance assigned to
    `self._rpc`. The base class provides a `call()` helper that forwards
    to the active connection, and a `handle_request(method, params)` hook
    which may be overridden or supplied via the `req_handler` constructor
    argument.

    Constructor:
      - `port` (int): TCP port to bind/connect to.
      - `req_handler` (callable|None): optional request handler.
      - `timeout` (int|float): operation timeout in seconds.

    Behavior:
      - `call()` raises `ETUMRuntimeError` if no active connection exists.
    """

    def __init__(
        self,
        host,
        port,
        req_handler: Callable[[dict], Any] = None,
        timeout=10,
        dbg_out=None,
    ):
        super().__init__()
        self._host = host
        self._port = port
        self._timeout = timeout
        self._rpc = None
        self._req_handler = req_handler
        self._dbg_out = dbg_out
        self._event_ready = threading.Event()

    def handle_request(self, method, params):
        """Override to implement server-side request handling.

        The default implementation delegates to the `req_handler` provided
        at construction (if any). Override this method to customize
        behaviour.
        """
        if self._req_handler is not None:
            return self._req_handler(method, params)

        self.print_info("No handler defined for the calls")

    def call(self, method, params):
        if (self._rpc is not None) and self._rpc.running:
            return self._rpc.call(method, params)
        else:
            raise ETUMRuntimeError(f"'{self.name}' JRPC Server not started.")

    def print_info(self, msg):
        if self.dbg_out is not None:
            print(f"{self.name}: " + str(msg), file=self.dbg_out)

    def run(self):
        pass

    def stop(self):
        if self._rpc is not None:
            self._rpc.stop()

    def connect(self, sock):
        self._rpc = JsonRpcConnection(
            self.name, sock, self.handle_request, dbg_out=self.dbg_out
        )
        self._rpc.wait_ready()
        self._event_ready.set()

    def wait_ready(self, timeout=None):
        return self._event_ready.wait(timeout)

    @property
    def dbg_out(self):
        return self._dbg_out

    @dbg_out.setter
    def dbg_out(self, dbg_out):
        self._dbg_out = dbg_out
        if self._rpc is not None:
            self._rpc.dbg_out = dbg_out


class JsonRpcSrv(JsonRpcBase):
    """Single-connection JSON-RPC server.

    `JsonRpcSrv` binds to `localhost` on the provided port and waits for a
    single client connection. When a client connects it creates a
    `JsonRpcConnection` and runs until the connection closes or is stopped.

    Typical usage::

        srv = JsonRpcSrv(port, req_handler=my_handler)
        srv.start()  # runs in background thread

    The server will raise `ETUMRuntimeError` on accept/connect timeout.
    """

    def __init__(self, host, port, req_handler=None, timeout=10):
        super().__init__(host, port, req_handler, timeout)
        self.name = f"JsonRpcSvr_{port}"

    def run(self):
        # TCP/IP socket creation
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                # Link of the socket at the configured port
                sock.bind((self._host, self._port))

                # Listens incoming connections
                sock.listen(1)
                self.print_info(f"listening on {self._host}:{self._port}")

                self.print_info(f"awaiting connection for {self._timeout} secs")
                sock.settimeout(self._timeout)
                while True:
                    try:
                        conn, addr = sock.accept()
                        break
                    except socket.timeout:
                            raise ETUMRuntimeError(f"{self.name}: Timeout")

                self.print_info("Client connected")
                with conn:
                    self.connect(conn)

                    while self._rpc.running:
                        # Sleep a short time to avoid a busy loop and allow
                        # the receiver thread to process messages.
                        sleep(0.1)

        finally:
            if self._rpc is not None:
                self._rpc.stop()
                self._rpc.join()
            self.print_info("stopped")


class JsonRpcClient(JsonRpcBase):
    """Simple JSON-RPC client that connects to a server on localhost.

    `JsonRpcClient` will attempt to connect to the given port until the
    configured timeout elapses. On successful connection it creates a
    `JsonRpcConnection` and serves requests/responses until closed.

    Typical usage::

        clt = JsonRpcClient(host, port)
        clt.start()
        resp = clt.call('method', {'a': 1})
    """

    def __init__(self, host, port, req_handler=None, timeout=10):
        super().__init__(host, port, req_handler, timeout)
        self.name = f"JsonRpcClt_{port}"

    def run(self):
        if tm.OS() == "Windows":
            self.run_win()
        else:
            self.run_lin()

    def run_win(self):
        # TCP/IP socket creation
        tslice = 1
        t = self._timeout
        sock = None
        try:
            while t >= 0:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(tslice)
                # Link of the socket at the configured port
                try:
                    sock.connect((self._host, self._port))
                    break
                except socket.timeout:
                    sock.close()
                    t -= tslice
                    if t < 0:
                        raise ETUMRuntimeError(
                            f"{self.name}: failed to connect : timeout"
                        )
                    else:
                        sleep(tslice)
                except socket.error as e:
                    raise ETUMRuntimeError(f"{self.name}: failed to connect : {e}")

            self.print_info("Connected to server")
            self.connect(sock)

            while self._rpc.running:
                # Sleep a short time to avoid a busy loop and allow
                # the receiver thread to process messages.
                sleep(0.1)

        finally:
            if sock is not None:
                sock.close()
            if self._rpc is not None:
                self._rpc.stop()
                self._rpc.join()
            self.print_info("closed")

    def run_lin(self):
        # TCP/IP socket creation
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                tslice = 0.1
                t0 = monotonic()
                sock.settimeout(0)
                # Link of the socket at the configured port
                while True:
                    try:
                        sleep(tslice)
                        sock.connect((self._host, self._port))
                        break
                    except Exception as e:
                        if (monotonic() - t0) > self._timeout:
                            raise ETUMRuntimeError(
                                f"{self.name}: failed to connect : {e}"
                            )

                self.print_info("Connected to server")
                self.connect(sock)

                while self._rpc.running:
                    # Sleep a short time to avoid a busy loop and allow
                    # the receiver thread to process messages.
                    sleep(0.1)

        finally:
            if self._rpc is not None:
                self._rpc.stop()
                self._rpc.join()
            self.print_info("closed")
