from datetime import datetime
import sys
import os
import re
import errno
import codecs
import time
from queue import Queue, Empty
from time import sleep
import serial
import threading

from telnetlib3 import Telnet, DO, WILL, WONT, TTYPE, IAC, SB, SE, theNULL

from runtime.tum_except import ETUMRuntimeError

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

    def get_available(self, block=False, timeout=None):
        """Every buffered byte at once; b'' when nothing arrived in time."""
        with self.cond:
            if block and len(self.items) == 0:
                self.cond.wait(timeout)
            items = self.items
            self.items = b''
            return items

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
        # Set the attributes __del__ relies on first, so a failure further down
        # leaves a partially-built object the GC can still finalize cleanly.
        self.isOpened = False
        self.port = None
        self.stream = sys.stdout
        self.name = name
        self.encoding = "utf-8"
        self.echo_on = echoOn
        self.write_delay = write_delay
        # Bytes read past a read_until match, served before the transport.
        self._pending = b''
        # Line ending appended by writeln.
        self.newline = '\n'
        self.string_buffer = '['+str(datetime.now()).split('.')[0].split(' ')[1]+' '+self.name+']'

    def __del__(self):
        """ This is a safeguard that tries to close the telnet connection, in case it was not done,
        before the Console object is terminated by the garbage collector (GC).
        """
        if getattr(self, "isOpened", False):
            name = getattr(self, "name", None)
            who = ("console '{}' ({})".format(name, type(self).__name__)
                   if name else type(self).__name__)
            print('Warning: {} is about to be deleted but the connection was not closed. '
                  'A close() call is missing somewhere in your code!'.format(who))
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

    def _ensure_open(self):
        """Raise a clear error when an IO method runs on a console whose open()
        never ran or failed, instead of a raw AttributeError on the missing
        underlying transport (telnet/ssh session, serial port, socket, …)."""
        if not getattr(self, "isOpened", False):
            raise ETUMRuntimeError(
                "console '{}' is not open: its open action failed, never ran, "
                "or it was closed".format(getattr(self, "name", "?"))
            )

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

    # Max chars of the buffer tail scanned in regex mode (bounds cost/memory).
    REGEX_WINDOW = 65536

    def read_available(self, timeout):
        """One chunk of available bytes; None or b'' when nothing arrived.
        Default: a single readchar, so external subclasses keep working."""
        return self.readchar(timeout)

    def _next_chunk(self, timeout):
        """Bytes pushed back by a previous read, else a transport chunk."""
        if self._pending:
            data, self._pending = self._pending, b''
            return data
        return self.read_available(timeout)

    def _push_back(self, data):
        """Return bytes read past a match; served first by the next read."""
        self._pending = data + self._pending

    def _pending_text(self):
        """Drain the pushed-back bytes as text (for read_nowait)."""
        data, self._pending = self._pending, b''
        return data.decode(self.encoding, errors='replace')

    def _emit_line(self):
        self.string_buffer = self.string_buffer.replace('\r\n', '\n')
        self.string_buffer = self.string_buffer.replace('\r', '')
        self.stream.write(self.string_buffer)
        date_str = str(datetime.now()).split('.')[0].split(' ')[1]
        self.string_buffer = '[{} {}]'.format(date_str, self.name)

    def _display(self, text, final=False):
        """Append *text* to the dated line buffer, flushing complete lines
        (one dated header per line, as the GUI log expects)."""
        parts = text.split('\n')
        for part in parts[:-1]:
            self.string_buffer += part + '\n'
            self._emit_line()
        self.string_buffer += parts[-1]
        if final and parts[-1] != '':
            self.string_buffer += '\n'
            self._emit_line()

    def _find_match(self, read_data, prev_len, matches, compiled):
        """Earliest match end in *read_data*, or None. Sets self._matched."""
        end = None
        if compiled is not None:
            tail = read_data[-self.REGEX_WINDOW:]
            offset = len(read_data) - len(tail)
            for p in compiled:
                m = p.search(tail)
                if m is not None and (end is None or offset + m.end() < end):
                    end = offset + m.end()
                    self._matched = m.group(0)
        else:
            for m in matches:
                pos = read_data.find(m, max(0, prev_len - len(m) + 1))
                if pos != -1 and (end is None or pos + len(m) < end):
                    end = pos + len(m)
                    self._matched = m
        return end

    def read_until(self, match, timeout=None, return_data=False, mute=False,
                   should_stop=None, regex=False):
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
        self._ensure_open()
        read_data = ''
        status = -1
        if not match:
            raise ETUMRuntimeError(
                "'expected' pattern can not be empty "
                "(got {!r})".format(match))

        # match: a string or list of strings; succeed as soon as any is seen.
        if isinstance(match, (list, tuple)):
            matches = [str(m) for m in match]
        else:
            matches = [str(match)]
        for idx, m in enumerate(matches):
            if len(m) == 0:
                raise ETUMRuntimeError(
                    "'expected' pattern can not be empty: entry {} of {!r} is "
                    "empty".format(
                        idx, matches))

        compiled = None
        if regex:
            # 'matches' are regular expressions; succeed on the first hit.
            compiled = []
            for m in matches:
                try:
                    compiled.append(re.compile(m))
                except re.error as e:
                    raise ETUMRuntimeError(
                        "Invalid regular expression {!r}: {}".format(m, e)) from None
        self._matched = None

        # A multi-byte sequence split across chunks decodes once complete.
        decoder = codecs.getincrementaldecoder(self.encoding)('replace')

        # timeout == 0: return what is buffered now; otherwise wait for the
        # match up to the deadline (forever when timeout is None), polling in
        # short reads so a stop request is honored within STOP_POLL_INTERVAL.
        drain = timeout is not None and timeout < TIMEOUT_NULL
        deadline = None
        if drain:
            self.set_read_timeout(0)
        else:
            if timeout is not None:
                deadline = time.monotonic() + timeout
            self.set_read_timeout(STOP_POLL_INTERVAL)

        while status < 0:
            if should_stop is not None and should_stop():
                break
            if drain:
                raw = self._next_chunk(0)
                if raw is None or raw == b'':
                    break
            else:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                raw = self._next_chunk(STOP_POLL_INTERVAL)
                if raw is None or raw == b'':
                    continue

            chunk = decoder.decode(raw)
            if chunk == '':
                continue
            prev_len = len(read_data)
            read_data += chunk

            end = self._find_match(read_data, prev_len, matches, compiled)
            if end is None:
                if not mute:
                    self._display(chunk)
                continue
            status = 0
            # The stream stays positioned right after the match: bytes read
            # past it are pushed back for the next read.
            extra = read_data[end:]
            if extra or decoder.getstate()[0]:
                self._push_back(extra.encode(self.encoding)
                                + decoder.getstate()[0])
            read_data = read_data[:end]
            if not mute:
                self._display(chunk[:end - prev_len], final=True)

        if return_data:
            return status, read_data
        return status

    def _mirror_write(self, characters, mute):
        """Local display of what is sent, when echoOn is set."""
        if self.echo_on and not mute:
            ech = '' if characters.strip(' ').endswith('\n') else '\n'
            print(('[>' + self.name + '] : ' + characters), end=ech)

    def writeln(self, characters, mute=False):
        return self.write(characters + self.newline, mute)

    def write(self, characters, mute=False):
        self._ensure_open()
        self._mirror_write(characters, mute)
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
                msg = 'WARN: could not connect to telnet {}:{} ({}), retrying in {} seconds...'.format(
                    self.host, self.port_id, exc, mdelay)
                print(msg)
                sleep(mdelay)
                mtries -= 1
                mdelay *= 2
        else:
            try:
                self.port = Telnet(self.host, self.port_id)
            except OSError as exc:
                raise ETUMRuntimeError(
                    "could not connect to telnet {}:{} for console '{}': {}".format(
                        self.host, self.port_id, self.name, exc)) from None

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

    def read_available(self, timeout):
        # First byte through expect (drives the telnet negotiation), then
        # whatever else already arrived.
        first = self.readchar(timeout)
        if first is None or first == b'':
            return first
        return first + self.port.read_very_eager()

    def readline(self):
        return self.read_until('\n', return_data=True)[1]

    def read_nowait(self, mute=False):
        self._ensure_open()
        st = self._pending_text() + self.port.read_very_eager().decode(
            self.encoding, errors='replace')
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


def _serial_open_error_message(port_id, exc):
    """Build a short, direct message for a failed serial open."""
    errno_ = getattr(exc, "errno", None)
    if errno_ == errno.ENOENT:
        return "Serial device '{}' does not exist.".format(port_id)
    if errno_ == errno.EACCES:
        return ("Permission denied opening serial device '{}' "
                "(is your user allowed to access it, e.g. 'dialout' group?)."
                .format(port_id))
    return "Could not open serial device '{}': {}".format(port_id, exc)


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
        self._thd = None

    def open(self):
        try:
            self.port = serial.Serial(port=self.port_id,
                                      baudrate=self.baudrate,
                                      stopbits=self.stopbits,
                                      parity=self.parity,
                                      xonxoff=self.xonxoff,
                                      timeout=None)
        except (serial.SerialException, OSError) as e:
            raise ETUMRuntimeError(self._open_error_message(e)) from None
        self.isOpened = True
        if self.bufferize:
            self.port.timeout = 2
            self._thd = threading.Thread(target=self.read_thread)
            self._thd.start()

    def _open_error_message(self, exc):
        return _serial_open_error_message(self.port_id, exc)

    def read_thread(self):
        while not self.stop.is_set():
            c = self.port.read(1)
            if c:
                self.rx_queue.put(c)

    def close(self):
        if self.bufferize and self._thd is not None:
            self.stop.set()
            self._thd.join()
        if self.port is not None:
            self.port.close()
            self.isOpened = False

    def set_read_timeout(self, timeout):
        if not self.bufferize:
            self.port.timeout = timeout

    def _check_reader(self):
        if not self._thd.is_alive() and not self.stop.is_set():
            raise ETUMRuntimeError(
                "cannot read serial console '{}' ({}): its background reader "
                "thread is not running".format(self.name, self.port_id))

    def readchar(self, timeout):
        if not self.isOpened:
            raise ETUMRuntimeError(
                "serial console '{}' ({}) is not open".format(self.name, self.port_id))
        if self.bufferize:
            self._check_reader()
            if timeout < TIMEOUT_NULL:
                return self.rx_queue.get(block=False)
            else:
                return self.rx_queue.get(block=True, timeout=timeout)

        return self.port.read(1)

    def read_available(self, timeout):
        if not self.isOpened:
            raise ETUMRuntimeError(
                "serial console '{}' ({}) is not open".format(self.name, self.port_id))
        if self.bufferize:
            self._check_reader()
            return self.rx_queue.get_available(block=timeout >= TIMEOUT_NULL,
                                               timeout=timeout)
        self.port.timeout = timeout
        first = self.port.read(1)
        if first == b'':
            return first
        waiting = self.port.in_waiting
        return first + (self.port.read(waiting) if waiting else b'')

    def _push_back(self, data):
        if self.bufferize:
            self.rx_queue.pushBack(data)
        else:
            super()._push_back(data)

    def flush(self):
        self.port.flush()

    def read_nowait(self, mute=False):
        if not self.isOpened:
            raise ETUMRuntimeError(
                "serial console '{}' ({}) is not open".format(self.name, self.port_id))
        if self.bufferize:
            self._check_reader()
            st = self.rx_queue.getAll().decode(self.encoding, errors='replace')
            if not mute:
                date_str = str(datetime.now()).split('.')[0].split(' ')[1]
                self.stream.write('[{} {}]'.format(date_str, self.name)+st)
            return st

        st = self._pending_text() + self.port.read(
            self.port.in_waiting).decode(self.encoding, errors='replace')
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
            raise ConnectionAbortedError(
                "console '{}' closed while reading".format(self.name))
        try:
            return self.rx_queue.get(timeout=timeout)
        except Empty:
            return None

    def read_available(self, timeout):
        first = self.readchar(timeout)
        if first is None:
            return None
        data = first
        try:
            while True:
                data += self.rx_queue.get_nowait()
        except Empty:
            return data

    def read_nowait(self, mute=False):
        if self.log_fd is None:
            raise ConnectionAbortedError(
                "console '{}' closed while reading".format(self.name))
        chars = self._pending_text()
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
        try:
            self.port = serial.Serial(port=self.port_id, baudrate=self.baudrate, timeout=None)
        except (serial.SerialException, OSError) as e:
            raise ETUMRuntimeError(_serial_open_error_message(self.port_id, e)) from None
        super().open()


class TelnetLoggedConsole(LoggedConsole):
    TYPE = 'telnet'

    def __init__(self, name, host, port=23,  overwriteFile=True, echoOn=False, logPath='', write_delay=0):
        super().__init__(name, overwriteFile, echoOn, logPath, write_delay)
        self.port = None
        self.host = host
        self.port_id = port

    def open(self):
        try:
            self.port = Telnet(self.host, self.port_id)
        except OSError as exc:
            raise ETUMRuntimeError(
                "could not connect to telnet {}:{} for console '{}': {}".format(
                    self.host, self.port_id, self.name, exc)) from None
        super().open()

    def _readPort(self, timeout=0.2):
        try:
            c = self.port.expect([re.compile(b'.{1}', re.DOTALL), ], timeout)[2]
        except (ConnectionAbortedError, ConnectionResetError):
            return None
        return c
