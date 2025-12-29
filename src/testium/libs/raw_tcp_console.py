from datetime import datetime
import sys
import socket
import traceback

from libs.console import *

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
            raise Exception('Already connected to the target')
        else:
            try:
                _socket = socket.create_connection((self.address, self.port))
                self.sock = _socket
                self.isOpened = True
                self.sock.settimeout(self.stimeout)
            except:
                if _socket is not None:
                    _socket.close()
                traceback.print_exception(*sys.exc_info())
                self.sock = None

    def close(self):
        try:
            if self.sock != None:
                self.sock.close()
                self.sock = None
            self.isOpened = False
        except:
            pass

    def set_read_timeout(self, timeout):
        if self.stimeout != timeout:
            self.sock.settimeout(timeout)
            self.stimeout = timeout

    def readchar(self, timeout):
        c = ''.encode()
        try:
            c = self.sock.recv(1)
        except:
            pass
        return c

    def read_nowait(self, mute=False):
        s = ''.encode()
        self.sock.settimeout(0)
        self.stimeout = 0
        s = self.sock.recv(4096)
        st = s.decode('utf-8', errors='replace')
        if not mute:
            date_str = str(datetime.now()).split('.')[0].split(' ')[1]
            self.stream.write('[{} {}]'.format(date_str, self.name)+st)
        return st

    def write(self, s, mute=False):
        if self.echo_on and not mute:
            ech = '' if s.strip(' ').endswith('\n') else '\n'
            print(('[>' + self.name + '] : ' + s), end=ech)
        res = self.sock.sendall(s.encode('utf-8'))
        return res
