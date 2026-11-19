import sys
import locale
if sys.platform.startswith('win'):
    import subprocess
else:
    import pexpect
import threading
import os
import time

ourPath = os.path.dirname(__file__)
sys.path.append(ourPath)
from api.console import (Console, BytesStore, TIMEOUT_NULL, _char_ts,
                         _byte_ts)
from runtime.tum_except import ETUMRuntimeError

class TermConsole(Console):
    TYPE = 'term'

    def __init__(self, name, project_path=None, cust_shell=None, echoOn=False, write_delay=0):
        Console.__init__(self, name, echoOn, write_delay)
        if sys.platform.startswith('win'):
            # cmd uses the active console code page (65001 in a UTF-8
            # terminal, not always cp850); 'oem' when no console is attached.
            import ctypes
            cp = ctypes.windll.kernel32.GetConsoleOutputCP()
            self.encoding = f'cp{cp}' if cp else 'oem'
        
        if not project_path:
            self.ppath = os.getcwd()
        else:
            self.ppath = project_path
        self.cust_shell = cust_shell
        self.stop = threading.Event()

        self.term = None

    def __del__(self):
        if self.term is not None:
            try:
                self.term.kill()
            except OSError:
                pass
            self.term = None

    def enqueue_output(self):
        if sys.platform.startswith('win'):
            while not self.stop.is_set():
                try:
                    c = self.term.stdout.read(1)
                except (ValueError, OSError):
                    break
                if c is not None:
                    self.q.put(time.time(), c)
        else:
            while not self.stop.is_set():
                try:
                    c = self.term.read_nonblocking(1, timeout=0.2)
                except pexpect.TIMEOUT:
                    continue
                except (pexpect.EOF, OSError):
                    break
                if c is not None:
                    # Stamp the byte at reception: the display path stamps
                    # each log line with the time its first character
                    # arrived, not the time it is drained.
                    self.q.put(time.time(), c)

    def open(self):

        if (self.cust_shell == None):
            if sys.platform.startswith('win'):
                shell_cmd = ['cmd.exe']
            else:
                shell_cmd = '/bin/sh'
        else:
            shell_cmd = self.cust_shell


        if sys.platform.startswith('win'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.term = subprocess.Popen(shell_cmd,
                                   shell=False,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   universal_newlines=False,
                                   startupinfo=startupinfo,
                                   cwd=self.ppath,
                                   bufsize=0)

        else:
            # In Flatpak this returns a `flatpak-spawn --host` wrapper so the
            # console behaves like a host shell (matching py_func / lua_func /
            # run); elsewhere it's the chosen command unchanged.
            from interpreter.utils import bins
            argv = bins.host_console_command(shell_cmd, self.ppath)
            try:
                self.term = pexpect.spawn(argv[0], args=argv[1:],
                                          echo=False, cwd=self.ppath)
            except pexpect.ExceptionPexpect as e:
                raise ETUMRuntimeError(
                    "could not start shell {!r} in directory '{}' for console "
                    "'{}': {}".format(shell_cmd, self.ppath, self.name, e)) from None

        self.q = BytesStore()
        self.t = threading.Thread(target=self.enqueue_output)
        self.t.daemon = True # thread dies with the program
        self.t.start()
        self.isOpened = True

    def close(self):
        self.stop.set()
        if getattr(self, 't', None) is not None:
            self.t.join(1)
        if self.term is not None:
            try:
                self.term.terminate()
            except OSError:
                pass
            self.term = None
        self.isOpened = False

    def readchar(self, timeout):
        item = self.q.get(block=timeout >= TIMEOUT_NULL, timeout=timeout)
        if item is None:
            return None
        data, ts = item
        return data, [ts]

    def read_available(self, timeout):
        return self.q.get_available(block=timeout >= TIMEOUT_NULL,
                                    timeout=timeout)

    def _push_back(self, data, ts=None):
        self.q.pushBack(data, ts)

    def read_nowait(self, mute=False):
        self._ensure_open()
        data, ts = self.q.getAll()
        st = data.decode(self.encoding, errors='replace')
        if st == '':
            return st
        # ts[i] is the reception time of data[i] (one per byte); a line stamp
        # is the time of its first character (the first byte of a multi-byte
        # sequence).
        char_ts = _char_ts(data, ts, len(st))
        if st[-1] not in '\r\n':
            # Incomplete last line: push it back — with its reception times —
            # so the next read serves it with the same stamps. The store keeps
            # bytes, so the per-character times are expanded over the
            # re-encoded bytes.
            i = st.rfind('\n')
            back = st[i + 1:]  # nonempty: st ends without a newline
            self.q.pushBack(back.encode(self.encoding),
                            _byte_ts(back, char_ts[i + 1:], self.encoding))
            st, char_ts = st[:i + 1], char_ts[:i + 1]
            if st == '':
                return st
        self._display_raw(st, char_ts, mute)
        return st

    def write(self, s, mute=False):
        self._ensure_open()
        self._mirror_write(s, mute)
        if sys.platform.startswith('win'):
            res = self.term.stdin.write(s.encode(self.encoding))
        else:
            res = self.term.send(s)

        return res
