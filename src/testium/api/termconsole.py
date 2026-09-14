from datetime import datetime
import sys
import locale
if sys.platform.startswith('win'):
    import subprocess
else:
    import pexpect
import threading
import os

ourPath = os.path.dirname(__file__)
sys.path.append(ourPath)
from api.console import (Console, BytesStore, TIMEOUT_NULL)
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
                    self.q.put(c)
        else:
            while not self.stop.is_set():
                try:
                    c = self.term.read_nonblocking(1, timeout=0.2)
                except pexpect.TIMEOUT:
                    continue
                except (pexpect.EOF, OSError):
                    break
                if c is not None:
                    self.q.put(c)

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
        if timeout < TIMEOUT_NULL:
            c = self.q.get(block=False)
            return c
        else:
            c = self.q.get(block=True, timeout=timeout)
            return c

    def read_available(self, timeout):
        return self.q.get_available(block=timeout >= TIMEOUT_NULL,
                                    timeout=timeout)

    def _push_back(self, data):
        self.q.pushBack(data)

    def read_nowait(self, mute=False):
        self._ensure_open()
        s = ''.encode()

        s += self.q.getAll()

        st = s.decode(self.encoding, errors='replace')

        ls = st.splitlines()
        if (len(st) > 0) and (st[-1] != '\r') and (st[-1] !='\n'):
            self.q.pushBack(ls[-1].encode())
            ls = ls[0:-1]

        st = '\n'.join(ls)
        if not mute:
            date_str = str(datetime.now()).split('.')[0].split(' ')[1]
            self.stream.write('[{} {}]'.format(date_str, self.name)+st)
        return st

    def write(self, s, mute=False):
        self._ensure_open()
        self._mirror_write(s, mute)
        if sys.platform.startswith('win'):
            res = self.term.stdin.write(s.encode(self.encoding))
        else:
            res = self.term.send(s)

        return res
