from datetime import datetime
import sys
import socket
import traceback

from api.console import *

class RawTCPConsole(Console):
    TYPE = 'rawtcp'

    def __init__(self, name, address, port, echoOn=False, write_delay=0):
        super().__init__(name, echoOn, write_delay)
        self.sock = None
        self.address = address
        self.port = int(port)
        self.stimeout = 0

    def open(self):
        #if trying to connect when already connected.
        _socket = None
        if self.sock is not None:
            raise ETUMRuntimeError(
                f"Raw TCP console already connected to "
                f"{self.address}:{self.port}.")
        else:
            try:
                _socket = socket.create_connection((self.address, self.port))
                _socket.settimeout(self.stimeout)
                self.sock = _socket
                self.isOpened = True
            except OSError as e:
                if _socket is not None:
                    _socket.close()
                self.sock = None
                self.isOpened = False
                raise ETUMRuntimeError(
                    f"Raw TCP connection to {self.address}:{self.port} "
                    f"failed: {e}")

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        self.isOpened = False

    def set_read_timeout(self, timeout):
        if self.stimeout != timeout:
            self.sock.settimeout(timeout)
            self.stimeout = timeout

    def _recv(self, size):
        """b'' when nothing arrived in time; clear error on a broken link."""
        try:
            return self.sock.recv(size)
        except (socket.timeout, BlockingIOError):
            return b''
        except OSError as e:
            raise ETUMRuntimeError(
                "Raw TCP read on console '{}' ({}:{}) failed: {}".format(
                    self.name, self.address, self.port, e)) from None

    def readchar(self, timeout):
        data = self._recv(1)
        if not data:
            return None
        return data, [time.time()]

    def read_available(self, timeout):
        self.set_read_timeout(timeout)
        data = self._recv(4096)
        if not data:
            return None
        return data, [time.time()] * len(data)

    def read_nowait(self, mute=False):
        self._ensure_open()
        self.sock.settimeout(0)
        self.stimeout = 0
        pend_text, pend_ts = self._pending_text()
        now = time.time()
        data = self._recv(4096)
        st = pend_text + data.decode(self.encoding, errors='replace')
        self._display_raw(st, pend_ts + [now] * len(data), mute)
        return st

    def write(self, s, mute=False):
        self._ensure_open()
        self._mirror_write(s, mute)
        res = self.sock.sendall(s.encode(self.encoding))
        return res
