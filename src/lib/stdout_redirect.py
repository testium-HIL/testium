import sys
import threading
from threading import (Thread, Event)
from lib.string_queue import StringQueue
from time import (sleep)


class StdoutProxy:
    """Thread-aware stdout proxy.

    Each writing thread can be associated with:
      - a per-thread buffer (StringQueue) where its writes are captured for the
        per-item SQLite log column;
      - a 'branch' label, used to prefix each line in the live (parent-visible)
        output stream so concurrent branches are easy to read.

    Threads with no association fall back to the default buffer (the "main"
    thread's buffer) and write to live output without prefix.
    """

    def __init__(self, live_stream, default_buffer):
        self.live_stream = live_stream
        self.default_buffer = default_buffer
        self._buffers = {}
        self._branches = {}
        self._lock = threading.Lock()

    def register(self, tid=None, buffer=None, branch=None):
        if tid is None:
            tid = threading.get_ident()
        with self._lock:
            if buffer is not None:
                self._buffers[tid] = buffer
            if branch is not None:
                self._branches[tid] = branch

    def unregister(self, tid=None):
        if tid is None:
            tid = threading.get_ident()
        with self._lock:
            self._buffers.pop(tid, None)
            self._branches.pop(tid, None)

    def get_buffer(self, tid=None):
        if tid is None:
            tid = threading.get_ident()
        with self._lock:
            return self._buffers.get(tid, self.default_buffer)

    def write(self, s):
        if not s:
            return
        tid = threading.get_ident()
        with self._lock:
            buf = self._buffers.get(tid, self.default_buffer)
            branch = self._branches.get(tid)
        # Per-thread capture: clean, no prefix
        buf.write(s)
        # Live stream: prefix each line with the branch label
        if branch:
            self.live_stream.write(self._prefix(s, f'[{branch}] '))
        else:
            self.live_stream.write(s)

    @staticmethod
    def _prefix(s, prefix):
        ends_nl = s.endswith('\n')
        body = s[:-1] if ends_nl else s
        if body == '':
            return s
        prefixed = '\n'.join(prefix + line for line in body.split('\n'))
        if ends_nl:
            prefixed += '\n'
        return prefixed

    def writeln(self, s=''):
        self.write(s + '\n')

    def flush(self):
        try:
            self.live_stream.flush()
        except AttributeError:
            pass


class StdioRedirect:

    def __init__(self):
        self.redirect_enabled = False
        self.spy_enabled = False
        self.ini_stdout = sys.stdout
        self.ini_stderr = sys.stderr
        self.stream = self.ini_stdout

    def redirect(self, stream):
        if not self.spy_enabled:
            self.out_stream = stream
            self.stream = self.out_stream
            sys.stdout = self.out_stream
            sys.stderr = self.out_stream
            self.redirect_enabled = True

    def restore(self):
        if not self.spy_enabled and self.redirect_enabled:
            sys.stdout = self.ini_stdout
            sys.stderr = self.ini_stderr
            self.redirect_enabled = False

    def intercept(self):
        if not self.spy_enabled:
            self.log_buf = StringQueue()  # default buffer (main thread)
            self.proxy = StdoutProxy(self.out_stream, self.log_buf)
            sys.stdout = self.proxy
            sys.stderr = self.proxy
            self.stream = self.proxy
            self.spy_enabled = True

    def stop(self):
        if self.spy_enabled:
            sys.stdout = self.out_stream
            sys.stderr = self.out_stream
            self.stream = self.out_stream
            del self.log_buf
            del self.proxy

        self.spy_enabled = False

    def read(self):
        """Read accumulated content from the calling thread's buffer."""
        if not self.spy_enabled:
            return ''
        return self.proxy.get_buffer().read()

    def register_thread(self, buffer=None, branch=None):
        """Register the calling thread's per-thread buffer and/or branch label."""
        if self.spy_enabled:
            self.proxy.register(buffer=buffer, branch=branch)

    def unregister_thread(self):
        """Drop the calling thread's registration."""
        if self.spy_enabled:
            self.proxy.unregister()


stdio_redir = StdioRedirect()
