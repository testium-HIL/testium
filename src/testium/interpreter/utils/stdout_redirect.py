import sys
from threading import (Thread, Event)
from interpreter.utils.string_queue import StringQueue
from time import (sleep)

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
            self.thr_started = Event()
            self.log_buf = StringQueue()
            self.in_stream = StringQueue()
            self.stop_output = Event()
            self.thrd_out = Thread(target=self.interceptStdOut)
            self.thrd_out.daemon = True
            sys.stdout = self.in_stream
            sys.stderr = self.in_stream
            self.stream = self.in_stream
            self.thrd_out.start()
            self.thr_started.wait()
            self.spy_enabled = True


    def stop(self):
        if self.spy_enabled:
            sys.stdout = self.out_stream
            sys.stderr = self.out_stream
            self.stream = self.out_stream
            self.stop_output.set()
            self.thrd_out.join()
            del self.log_buf
            del self.in_stream
            del self.stop_output
            del self.thrd_out
            del self.thr_started

        self.spy_enabled = False

    def interceptStdOut(self):
        self.thr_started.set()
        while not self.stop_output.is_set():
            data = self.in_stream.read()
            self.log_buf.write(data)
            self.out_stream.write(data)
            if data == '':
                sleep(0.1)

    def read(self):
        ret = ''
        if self.spy_enabled:
            ret = self.log_buf.read()
        return ret

stdio_redir = StdioRedirect()
