# from io import (StringIO, SEEK_SET, SEEK_CUR, SEEK_END)
from multiprocessing import Queue
from queue import (Empty)
from threading import (Thread, Event, Condition)
from threading import Lock

class StringQueue(object):
    """ Class used to store the buffered consoles data:
         - SerialConsole
         - TermConsole
    """
    def __init__(self):
        self.cond = Condition()
        self.string = ''

    def write(self, data):
        with self.cond:
            self.string += data
            self.cond.notify() # Wake 1 thread waiting on cond (if any)

    def writeln(self, data=''):
        self.write(data + '\n')

    def read(self, block=False, timeout=None):
        ret = ''
        with self.cond:
            # If blocking is true, always return at least 1 item
            if block and len(self.string) == 0:
                self.cond.wait(timeout)
            if len(self.string) != 0:
                ret = self.string
                self.string = ''
        return ret
    
    def flush(self):
        pass

class BufferedStringQueue(StringQueue):
    def __init__(self, stream_out):
        super().__init__()
        self.stream_out = stream_out
        self.thr_started = Event()
        self.stop_evt = Event()
        self.thrd = Thread(target=self.loop)
        self.thrd.daemon = True
        self.thrd.start()
        self.thr_started.wait()

    def stop(self):
        self.stop_evt.set()
        self.thrd.join()
        del self.stop_evt
        del self.thrd
        del self.thr_started

    def loop(self):
        self.thr_started.set()
        while not self.stop_evt.is_set():
            data = self.read(True, 0.1)
            self.stream_out.write(data)
