from datetime import datetime
import sys
import os
import re
from queue import Queue, Empty
from time import sleep
import collections
import serial
import threading

from telnetlib3 import Telnet, DO, WILL, WONT, TTYPE, IAC, SB, SE, theNULL

TIMEOUT_NULL = 0.000001
STOP_POLL_INTERVAL = 0.2


class BytesStore(object):
    """ Class used to store the buffered consoles data:
         - SerialConsole
         - TermConsole
    """

    def __init__(self):
        self.cond = threading.Condition()
        self.items = b''

    def put(self, item):
        with self.cond:
            self.items += item
            self.cond.notify()  # Wake 1 thread waiting on cond (if any)

    def get(self, block=False, timeout=None):
        with self.cond:
            # If blocking is true, always return at least 1 item
            if block and len(self.items) == 0:
                self.cond.wait(timeout)
            if len(self.items) != 0:
                c = bytes([self.items[0]])
                self.items = self.items[1:]
                return c
            else:
                return None

    def getAll(self):
        with self.cond:
            items = self.items
            self.items = b''
        return items

    def pushBack(self, data):
        with self.cond:
            self.items = data + self.items


class Console(object):

    def __init__(self, name, echoOn=False, write_delay=0):
        self.stream = sys.stdout
        self.name = name
        self.encoding = "utf-8"
        self.echo_on = echoOn
        self.write_delay = write_delay
        self.string_buffer = '['+str(datetime.now()).split('.')[0].split(' ')[1]+' '+self.name+']'
        self.port = None
        self.isOpened = False

    def __del__(self):
        """ This is a safeguard that tries to close the telnet connection, in case it was not done,
        before the Console object is terminated by the garbage collector (GC).
        """
        if self.isOpened:
            print('Warning: {classname} is about to be deleted but the connection was not closed. \
A {classname}.close() is missing somewhere in your code !'.format(classname=type(self).__name__))
            self.close()

    def __enter__(self):
        """ Make Console a context manager and allow the use of the 'with ... as' statement
        """
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        """ Make Console a context manager and allow the use of the 'with ... as' statement
        """
        self.close()

    def set_read_timeout(self, timeout):
        pass

    def readchar(self, timeout):
        pass

    def read_nowait(self, mute=False):
        pass

    def flush(self):
        self.read_nowait(mute=True)

    def is_opened(self):
        return self.isOpened

    def _is_valid_character(self, data):
        """ return True if data is a valid ascii char [0x20-0x7E] or '\n' or '\r'
        """
        if data == '':
            return False

        # new line and carriage return are fine
        if data == '\n' or data == '\r':
            return True

        # reject all other non-ascii charaters
        code = ord(data)
        if code == 0x09:  # TAB
            return True
        if code <= 0x1f or code >= 0x7f:
            return False

        return True

    def _compute_char(self, data):
        c = data.decode(self.encoding, errors='replace')
        # if not self._is_valid_character(c):
        #    c = ''
        return c

    def read_until(self, match, timeout=None, return_data=False, mute=False, should_stop=None):
        """
        read until the string 'match is found
            If timeout is not set (None), this function runs indefinitely
            If timeout is set to zero, this function returns immediately
            If mute is set to True the characters read from the console will not be displayed
            If should_stop is a callable, it is polled between reads (every STOP_POLL_INTERVAL
            at most) and the loop exits early — like a timeout — when it returns True.

            If function fails (because of a timeout) it will return a 'status' integer set to -1
            otherwise it will return 0.
            The returned data may be a list in the form of [status, data] with the "data" string
            being the data read on the device when return_data has been set to true.
        """
        read_data = ''
        status = -1
        if not match:
            raise ValueError('match parameter can not be empty')

        if timeout is None:
            timeout = 1000000

        # Fixed-length queue that will contain the readout characters
        search_deque = collections.deque(maxlen=len(match))
        # convert match string into a deque for faster comparisons
        match_deque = collections.deque(match)

        # In case of a timeout equal to zero, it must be looped until the
        # buffer is empty
        # Otherwise we are waiting for the timeout to rise
        if timeout < TIMEOUT_NULL:
            self.set_read_timeout(0)
            data = self.readchar(0)

            while (status < 0) and ((data is not None) and (data != b'')):

                data = self._compute_char(data)

                if data != '':
                    if not mute:
                        self.string_buffer += data
                    read_data += data

                    search_deque.append(data)
                    if search_deque == match_deque:
                        status = 0
                        if (not mute) and (data != '\n'):
                            self.string_buffer += '\n'

                    if data == '\n' or (status >= 0):
                        # the datas are written line by line for display optimisation in GUI mode
                        if not mute:
                            self.string_buffer = self.string_buffer.replace('\r\n', '\n')
                            self.string_buffer = self.string_buffer.replace('\r', '')
                            self.stream.write(self.string_buffer)

                        date_str = str(datetime.now()).split('.')[0].split(' ')[1]
                        self.string_buffer = '[{} {}]'.format(date_str, self.name)

                if status < 0:
                    data = self.readchar(0)

        # Timeout different than zero
        else:
            # Poll in short chunks so a stop request is honored within
            # STOP_POLL_INTERVAL, regardless of the per-protocol blocking
            # behavior of readchar().
            self.set_read_timeout(STOP_POLL_INTERVAL)

            time_is_out = threading.Event()
            timer = threading.Timer(timeout, lambda: time_is_out.set())
            timer.start()

            try:
                while (status < 0) and (not time_is_out.is_set()):
                    if should_stop is not None and should_stop():
                        break

                    data = self.readchar(STOP_POLL_INTERVAL)
                    if data is not None:
                        data = self._compute_char(data)
                        if data != '':
                            if not mute:
                                self.string_buffer += data
                            read_data += data

                            search_deque.append(data)
                            if search_deque == match_deque:
                                status = 0
                                if (not mute) and (data != '\n'):
                                    self.string_buffer += '\n'

                            if data == '\n' or (status >= 0):
                                # the datas are written line by line for display optimisation in GUI mode
                                if not mute:
                                    self.string_buffer = self.string_buffer.replace('\r\n', '\n')
                                    self.string_buffer = self.string_buffer.replace('\r', '')
                                    self.stream.write(self.string_buffer)

                                date_str = str(datetime.now()).split('.')[0].split(' ')[1]
                                self.string_buffer = '[{} {}]'.format(date_str, self.name)
            finally:
                timer.cancel()

        if return_data:
            return status, read_data
        return status

    def write(self, characters, mute=False):
        if self.echo_on and not mute:
            ech = '' if characters.strip(" ").endswith('\n') else '\n'
            print(('[>' + self.name + '] : ' + characters), end=ech)
        if self.write_delay != 0:
            for char in characters:
                self.port.write(char.encode(self.encoding))
                sleep(self.write_delay)
            return len(characters)
        else:
            return self.port.write(characters.encode(self.encoding))


if not sys.platform.startswith('win'):
    # import SshConsole if pexpect is installed
    try:
        from api.console_ssh import SshConsole

    except ImportError:
        pass


class TelnetConsole(Console):
    TYPE = 'telnet'

    def __init__(self, name, host, port=23, echoOn=False, write_delay=0, tries=1, try_delay=2):

        super().__init__(name, echoOn, write_delay)
        self.port = None
        self.host = host
        self.port_id = port
        self.tries = tries
        self.try_delay = try_delay

    def open(self, user=None, pwd=None):

        mtries, mdelay = self.tries, self.try_delay
        while mtries > 1:
            try:
                self.port = Telnet(self.host, self.port_id)
                break
            except (TimeoutError, ConnectionRefusedError) as exc:
                msg = '{}, Retrying in {} seconds...'.format(str(exc), mdelay)
                print(msg)
                sleep(mdelay)
                mtries -= 1
                mdelay *= 2
        else:
            self.port = Telnet(self.host, self.port_id)

        self.isOpened = True

        if not user:
            return
        self.stream.write(self.port.read_until("login: "))
        self.port.write(user + "\n")

        self.stream.write(self.port.read_until("assword"))
        self.stream.write(self.port.read_until(":"))
        self.port.write(pwd + "\n")

    def readchar(self, timeout):
        return self.port.expect([re.compile(b'.{1}', re.DOTALL), ], timeout)[2]

    def readline(self):
        return self.read_until('\n', return_data=True)[1]

    def read_nowait(self, mute=False):
        st = self.port.read_very_eager().decode(self.encoding, errors='replace')
        if not mute:
            date_str = str(datetime.now()).split('.')[0].split(' ')[1]
            self.stream.write('[{} {}]'.format(date_str, self.name)+st)
        return st

    def close(self):
        if self.isOpened:
            self.port.close()
            self.isOpened = False

    def neg(self, sock, command, option):
        negotiation_list = [
            ['BINARY', WONT, 'WONT'],
            ['ECHO', WONT, 'WONT'],
            ['RCP', WONT, 'WONT'],
            ['SGA', WONT, 'WONT'],
            ['NAMS', WONT, 'WONT'],
            ['STATUS', WONT, 'WONT'],
            ['TM', WONT, 'WONT'],
            ['RCTE', WONT, 'WONT'],
            ['NAOL', WONT, 'WONT'],
            ['NAOP', WONT, 'WONT'],
            ['NAOCRD', WONT, 'WONT'],
            ['NAOHTS', WONT, 'WONT'],
            ['NAOHTD', WONT, 'WONT'],
            ['NAOFFD', WONT, 'WONT'],
            ['NAOVTS', WONT, 'WONT'],
            ['NAOVTD', WONT, 'WONT'],
            ['NAOLFD', WONT, 'WONT'],
            ['XASCII', WONT, 'WONT'],
            ['LOGOUT', WONT, 'WONT'],
            ['BM', WONT, 'WONT'],
            ['DET', WONT, 'WONT'],
            ['SUPDUP', WONT, 'WONT'],
            ['SUPDUPOUTPUT', WONT, 'WONT'],
            ['SNDLOC', WONT, 'WONT'],
            ['TTYPE', WILL, 'WILL'],
            ['EOR', WONT, 'WONT'],
            ['TUID', WONT, 'WONT'],
            ['OUTMRK', WONT, 'WONT'],
            ['TTYLOC', WONT, 'WONT'],
            ['VT3270REGIME', WONT, 'WONT'],
            ['X3PAD', WONT, 'WONT'],
            ['NAWS', WONT, 'WONT'],
            ['TSPEED', WONT, 'WONT'],
            ['LFLOW', WONT, 'WONT'],
            ['LINEMODE', WONT, 'WONT'],
            ['XDISPLOC', WONT, 'WONT'],
            ['OLD_ENVIRON', WONT, 'WONT'],
            ['AUTHENTICATION', WONT, 'WONT'],
            ['ENCRYPT', WONT, 'WONT'],
            ['NEW_ENVIRON', WONT, 'WONT']
        ]
        if ord(option) < 40:
            response = negotiation_list[ord(option)][1]
        else:
            response = WONT
        if command == DO:
            s = b''.join((IAC, response, option))
            sock.sendall(s)
        elif command == SE:
            s = ("%s%s%s%sDEC-VT100%s%s" % (IAC, SB, TTYPE, chr(0), IAC, SE))
            s = b''.join((IAC, SB, TTYPE, theNULL, b'DEC-VT100', IAC, SE))
            sock.sendall(s)
        return


class ETSConsole(TelnetConsole):
    TYPE = 'ETS'

    def open(self, port):
        TelnetConsole.open(self)
        self.port.set_option_negotiation_callback(self.neg)
        self.read_until("Username>", 5)
        self.write("rach_script\n")
        self.read_until(">", 2)
        self.write('c local port_'+str(port)+'\n')

        self.write("\r\n")
        self.read_until(">", 5)


class SerialConsole(Console):
    TYPE = 'serial'

    def __init__(self, name, port=None,  baudrate=9600, parity="none", stopbits=1, xonxoff=False,
                 bufferize=False, echoOn=False, write_delay=0):
        super().__init__(name, echoOn, write_delay)
        self.baudrate = baudrate
        self.bufferize = bufferize
        self.xonxoff = False
        if xonxoff:
            self.xonxoff = True
        self.parity = serial.PARITY_NONE
        if parity.lower() == "even":
            self.parity = serial.PARITY_EVEN
        if parity.lower() == "odd":
            self.parity = serial.PARITY_ODD
        self.stopbits = serial.STOPBITS_ONE
        if stopbits == 2:
            self.stopbits = serial.STOPBITS_TWO
        if bufferize:
            self.rx_queue = BytesStore()
            self.stop = threading.Event()
        self.port = None
        self.port_id = port

    def open(self):
        self.port = serial.Serial(port=self.port_id,
                                  baudrate=self.baudrate,
                                  stopbits=self.stopbits,
                                  parity=self.parity,
                                  xonxoff=self.xonxoff,
                                  timeout=None)
        self.isOpened = True
        if self.bufferize:
            self.port.timeout = 2
            self._thd = threading.Thread(target=self.read_thread)
            self._thd.start()

    def read_thread(self):
        while not self.stop.is_set():
            c = self.port.read(1)
            if c:
                self.rx_queue.put(c)

    def close(self):
        if self.bufferize:
            self.stop.set()
            self._thd.join()
        if self.port is not None:
            self.port.close()
            self.isOpened = False

    def set_read_timeout(self, timeout):
        if not self.bufferize:
            self.port.timeout = timeout

    def readchar(self, timeout):
        if self.bufferize:
            if not self._thd.is_alive() and not self.stop.isSet():
                raise RuntimeError(
                    "Impossible to read the serial console, it may be already openned")
            if timeout < TIMEOUT_NULL:
                return self.rx_queue.get(block=False)
            else:
                return self.rx_queue.get(block=True, timeout=timeout)

        return self.port.read(1)

    def flush(self):
        self.port.flush()

    def read_nowait(self, mute=False):
        if self.bufferize:
            if not self._thd.is_alive() and not self.stop.isSet():
                raise RuntimeError(
                    "Impossible to read the serial console, it may be already openned")
            st = self.rx_queue.getAll().decode(self.encoding, errors='replace')
            if not mute:
                date_str = str(datetime.now()).split('.')[0].split(' ')[1]
                self.stream.write('[{} {}]'.format(date_str, self.name)+st)
            return st

        st = self.port.read(self.port.inWaiting()).decode(self.encoding, errors='replace')
        if not mute:
            date_str = str(datetime.now()).split('.')[0].split(' ')[1]
            self.stream.write('[{} {}]'.format(date_str, self.name)+st)
        return st


class TelnetSerialConsole(TelnetConsole):
    TYPE = 'telnet&serial'

    def __init__(self, name, host, port=23, serial_port=None, baudrate=9600, echoOn=False, write_delay=0):
        Console.__init__(self, name, echoOn, write_delay)
        self.port = None
        self.host = host
        self.port_id = port
        self.serial_port = serial_port
        self.baudrate = baudrate

    def open(self, user=None, pwd=None):
        self.port = Telnet(self.host, self.port_id)
        self.isOpened = True
        if not user:
            return
        self.stream.write(self.port.read_until("login: "))
        self.port.write(user + "\n")
        self.stream.write(self.port.read_until("assword"))
        self.stream.write(self.port.read_until(":"))
        self.port.write(pwd + "\n")
        # then connect to the serial port using miniterm console
        self.stream.write(self.port.read_until("~]$"))
        self.stream.write("miniterm.py -p " + str(self.serial_port) +
                          " -b " + str(self.baudrate) + " --parity=N --lf\n")
        if (self.read_until("--- Miniterm on", 5) == -1):
            return


class LoggedConsole(Console):
    def __init__(self, name, overwriteFile=True, echoOn=False, logPath='', write_delay=0):
        super().__init__(name, echoOn, write_delay)
        self.rx_queue = Queue()
        self.stop = threading.Event()
        if logPath.endswith('.log'):
            if os.path.exists(os.path.dirname(logPath)):
                self.logfile_name = logPath
            else:
                os.makedirs(os.path.join(os.getcwd(), os.path.dirname(logPath)), exist_ok=True)
                self.logfile_name = os.path.join(os.getcwd(), logPath)
        else:
            if not os.path.isabs(logPath):
                logPath = os.path.join(os.getcwd(), logPath)
            os.makedirs(logPath, exist_ok=True)
            self.logfile_name = '{}/{}.log'.format(logPath, self.name)
        self.overwriteFile = overwriteFile
        if self.overwriteFile:
            open_mode = "w"
        else:
            open_mode = "a"
        # open with flush every new line
        self.log_fd = open(self.logfile_name, open_mode, buffering=1)

    def open(self):
        self.isOpened = True
        if self.log_fd is None:
            self.log_fd = open(self.logfile_name, "a", buffering=1)
        self._thd = threading.Thread(target=self.read_thread)
        self._thd.start()

    def _readPort(self):
        pass

    def read_thread(self):
        line_buffer = None
        while not self.stop.is_set():
            data = self._readPort()

            if data:
                self.rx_queue.put(data)
            else:
                continue
            data = data.decode(self.encoding, errors='replace')
            # if valid char, write into the file
            if self._is_valid_character(data):
                # replace '\r' by '\n' and '\r\n' by '\n'
                if data == '\r':
                    data = ''
                    continue
                 # date at reception of first new char of the line
                if line_buffer is None:
                    line_buffer = '['+str(datetime.now()).split('.')[0].split(' ')[1]+']'
                line_buffer += data
                if data == '\n':
                    # the datas are written line by line
                    self.log_fd.write(line_buffer)
                    line_buffer = None
        # if exit, flush data first
        if line_buffer is not None:
            self.log_fd.write(line_buffer)
        print('closing console "%s" log file' % (self.name))
        self.log_fd.close()
        self.log_fd = None

    def close(self):
        self.stop.set()
        self._thd.join()
        if self.port is not None:
            print('closing console "%s"' % (self.name))
            self.port.close()
            self.isOpened = False

    def readchar(self, timeout=None):
        if self.log_fd is None:
            raise ConnectionAbortedError
        try:
            return self.rx_queue.get(timeout=timeout)
        except Empty:
            return None

    def read_nowait(self, mute=False):
        if self.log_fd is None:
            raise ConnectionAbortedError
        chars = ''
        for _ in range(self.rx_queue.qsize()):
            chars = chars + self.rx_queue.get().decode(self.encoding, errors='replace')

        if not mute:
            date_str = str(datetime.now()).split('.')[0].split(' ')[1]
            self.stream.write('[{} {}]'.format(date_str, self.name)+chars)
        return chars


class SerialLoggedConsole(LoggedConsole):
    TYPE = 'serial'

    def __init__(self, name, port=None, baudrate=9600,  overwriteFile=True, echoOn=False, logPath='', write_delay=0):
        super().__init__(name, overwriteFile, echoOn, logPath, write_delay)
        self.baudrate = baudrate
        self.port = None
        self.port_id = port

    def _readPort(self):
        return self.port.read(1)

    def open(self):
        self.port = serial.Serial(port=self.port_id, baudrate=self.baudrate, timeout=None)
        super().open()


class TelnetLoggedConsole(LoggedConsole):
    TYPE = 'telnet'

    def __init__(self, name, host, port=23,  overwriteFile=True, echoOn=False, logPath='', write_delay=0):
        super().__init__(name, overwriteFile, echoOn, logPath, write_delay)
        self.port = None
        self.host = host
        self.port_id = port

    def open(self):
        self.port = Telnet(self.host, self.port_id)
        super().open()

    def _readPort(self, timeout=0.2):
        try:
            c = self.port.expect([re.compile(b'.{1}', re.DOTALL), ], timeout)[2]
        except (ConnectionAbortedError, ConnectionResetError):
            return None
        return c
