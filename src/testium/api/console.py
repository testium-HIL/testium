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


def _stamp_str(ts=None):
    """'HH:MM:SS' local time of a time.time() reception stamp
    (the display time when ts is None)."""
    if ts is None:
        ts = time.time()
    return time.strftime('%H:%M:%S', time.localtime(ts))


def _char_ts(consumed_bytes, ts, n_chars):
    """Reception time of the first byte of each of the *n_chars* characters
    decoded out of *consumed_bytes* (ts[i]: time of consumed_bytes[i]).

    A multi-byte sequence keeps the time of its first byte; with a
    single-byte encoding this is the per-character time. When the decoder
    emitted fewer characters than byte groups (a 'replace' error on a
    sequence that the decoder consumed whole), the time of the first byte of
    the group is reused for the missing characters.
    """
    out = []
    i = 0
    while i < len(consumed_bytes) and len(out) < n_chars:
        b = consumed_bytes[i]
        if b < 0x80:
            n = 1
        elif b < 0xC0:
            n = 1  # stray continuation byte: the decoder replaces it alone
        elif b < 0xE0:
            n = 2
        elif b < 0xF0:
            n = 3
        else:
            n = 4
        out.append(ts[i])
        i += n
    if out:
        # The decoder emitted fewer characters than byte groups (a 'replace'
        # error on a malformed sequence): reuse the last group's time.
        return out + [out[-1]] * (n_chars - len(out))
    return [None] * n_chars


def _byte_ts(text, char_ts, encoding):
    """Per-byte reception times of *text* once re-encoded: each character's
    time is repeated over the bytes of its encoding (so a pushed-back byte
    stream always carries one time per byte)."""
    out = []
    for ch, ts in zip(text, char_ts):
        out.extend([ts] * len(ch.encode(encoding)))
    return out


class BytesStore(object):
    """ Class used to store the buffered consoles data:
         - SerialConsole
         - TermConsole
    Each item carries the reception time (time.time()) of its bytes, so the
    display path can stamp a log line with the time its first character
    arrived instead of the time it is displayed.
    """

    def __init__(self):
        self.cond = threading.Condition()
        # list of (ts_list, data) segments: ts_list[i] is the reception
        # time of data[i]
        self.items = []

    def put(self, ts, data):
        with self.cond:
            self.items.append(([ts] * len(data), data))
            self.cond.notify()  # Wake 1 thread waiting on cond (if any)

    def get(self, block=False, timeout=None):
        with self.cond:
            # If blocking is true, always return at least 1 item
            if block and not self.items:
                self.cond.wait(timeout)
            if self.items:
                ts_list, data = self.items[0]
                if len(data) == 1:
                    self.items.pop(0)
                else:
                    self.items[0] = (ts_list[1:], data[1:])
                return data[:1], ts_list[0]
            else:
                return None

    def get_available(self, block=False, timeout=None):
        """Every buffered byte at once, with reception times;
        (b'', []) when nothing arrived in time."""
        with self.cond:
            if block and not self.items:
                self.cond.wait(timeout)
            self.items, items = [], self.items
        if not items:
            return b'', []
        return (b''.join(seg[1] for seg in items),
                [ts for seg in items for ts in seg[0]])

    def getAll(self):
        """Every buffered byte, with reception times; (b'', []) when empty."""
        with self.cond:
            self.items, items = [], self.items
        if not items:
            return b'', []
        return (b''.join(seg[1] for seg in items),
                [ts for seg in items for ts in seg[0]])

    def pushBack(self, data, ts=None):
        with self.cond:
            if ts is None:
                ts = [time.time()] * len(data)
            self.items.insert(0, (ts, data))


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
        # Bytes read past a read_until match (with their reception times),
        # served before the transport.
        self._pending = (b'', [])
        # Line ending appended by writeln.
        self.newline = '\n'
        # Shell dialect used by the exec action ('none': not a shell).
        self.dialect = 'none'
        # In-progress line of the display buffer: its text, and the reception
        # time of its first character (the stamp used when the line is emitted).
        self._line = ''
        self._line_ts = None
        # Reception times of the bytes currently held inside the read_until
        # decoder (a multi-byte sequence split across chunks).
        self._ts_hold = []

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
        """One stamped chunk of available bytes: (data, ts), ts[i] the
        reception time of data[i]; None or (b'', []) when nothing arrived.
        Default: a single readchar, so external subclasses keep working."""
        return self.readchar(timeout)

    def _next_chunk(self, timeout):
        """Stamped bytes pushed back by a previous read, else a transport chunk."""
        if self._pending[0]:
            pair, self._pending = self._pending, (b'', [])
            return pair
        return self.read_available(timeout)

    def _push_back(self, data, ts=None):
        """Return bytes read past a match (with their reception times);
        served first by the next read."""
        if ts is None:
            ts = [time.time()] * len(data)
        self._pending = (data + self._pending[0], ts + self._pending[1])

    def _pending_text(self):
        """Drain the pushed-back bytes as (text, ts): ts[i] is the reception
        time of the i-th byte (for read_nowait)."""
        (data, ts), self._pending = self._pending, (b'', [])
        return data.decode(self.encoding, errors='replace'), ts

    def _emit_line(self):
        """Flush the in-progress line, stamped with the reception time of
        its first character (the display time when it has none)."""
        line = self._line.replace('\r\n', '\n').replace('\r', '')
        self.stream.write('[{} {}]'.format(_stamp_str(self._line_ts),
                                           self.name) + line + '\n')
        self._line = ''
        self._line_ts = None

    def _display(self, text, ts, final=False):
        """Append *text* (ts[i]: reception time of text[i]) to the display
        buffer, flushing complete lines — each stamped with the reception
        time of its first character, as the file log does."""
        offset = 0
        parts = text.split('\n')
        for part in parts[:-1]:
            if self._line == '':
                self._line_ts = ts[offset]
            self._line += part
            self._emit_line()
            offset += len(part) + 1
        if parts[-1] != '':
            if self._line == '':
                self._line_ts = ts[offset]
            self._line += parts[-1]
        if final and parts[-1] != '':
            self._emit_line()

    def _display_raw(self, text, ts, mute):
        """Display a decoded (text, ts) pair (ts per byte) for read_nowait:
        each line is stamped with the reception time of its first character.
        With a single-byte encoding ts is also the per-character time; when
        the lengths differ (multi-byte sequences, 'replace' errors) the first
        stamp is reused for the whole text."""
        if mute or text == '':
            return
        if len(ts) == len(text):
            char_ts = ts
        else:
            char_ts = [ts[0] if ts else None] * len(text)
        self._display(text, char_ts, final=True)

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
        # The decoder is fresh for each call, so the held timestamps start
        # empty too (bytes held by a previous call were pushed back with
        # theirs, and are re-decoded here from scratch).
        decoder = codecs.getincrementaldecoder(self.encoding)('replace')
        self._ts_hold = []

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
                pair = self._next_chunk(0)
            else:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                pair = self._next_chunk(STOP_POLL_INTERVAL)
            if pair is None or pair[0] in (None, b''):
                if drain:
                    break
                continue

            raw, raw_ts = pair
            held = decoder.getstate()[0]
            chunk = decoder.decode(raw)
            if chunk == '':
                # A multi-byte sequence split across chunks: its bytes (and
                # their reception times) stay with the decoder state until
                # the sequence completes.
                self._ts_hold = self._ts_hold + raw_ts
                continue
            consumed = held + raw
            new_held = decoder.getstate()[0]
            # The line stamps need the time of the first byte of each
            # decoded character (a multi-byte sequence keeps its first byte).
            chunk_ts = _char_ts(consumed[:len(consumed) - len(new_held)],
                                self._ts_hold + raw_ts, len(chunk))
            self._ts_hold = (self._ts_hold + raw_ts)[len(consumed) - len(new_held):]
            prev_len = len(read_data)
            read_data += chunk

            end = self._find_match(read_data, prev_len, matches, compiled)
            if end is None:
                if not mute:
                    self._display(chunk, chunk_ts)
                continue
            status = 0
            # The stream stays positioned right after the match: bytes read
            # past it are pushed back for the next read, with their stamps.
            extra = read_data[end:]
            # The push-back stores bytes, so the per-character times of
            # 'extra' are expanded over its re-encoded bytes (a multi-byte
            # character re-encodes to more bytes than characters).
            extra_ts = _byte_ts(extra, chunk_ts[end - prev_len:],
                                self.encoding) + self._ts_hold
            if extra or new_held:
                self._push_back(extra.encode(self.encoding) + new_held, extra_ts)
            read_data = read_data[:end]
            if not mute:
                self._display(chunk[:end - prev_len], chunk_ts[:end - prev_len],
                              final=True)

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
        # The login banner is displayed as it arrives: each line is stamped
        # with the reception time (here arrival ≈ read, no reader thread).
        self._display_raw(self.port.read_until("login: ").decode(
            self.encoding, errors='replace'), None, mute=False)
        self.port.write(user + "\n")
        self._display_raw(self.port.read_until("assword").decode(
            self.encoding, errors='replace'), None, mute=False)
        self._display_raw(self.port.read_until(":").decode(
            self.encoding, errors='replace'), None, mute=False)
        self.port.write(pwd + "\n")

    def readchar(self, timeout):
        data = self.port.expect([re.compile(b'.{1}', re.DOTALL), ], timeout)[2]
        if not data:
            return None
        return data, [time.time()]

    def read_available(self, timeout):
        # First byte through expect (drives the telnet negotiation), then
        # whatever else already arrived.
        first = self.readchar(timeout)
        if first is None:
            return None
        rest = self.port.read_very_eager()
        return first[0] + rest, [first[1][0]] + [time.time()] * len(rest)

    def readline(self):
        return self.read_until('\n', return_data=True)[1]

    def read_nowait(self, mute=False):
        self._ensure_open()
        pend_text, pend_ts = self._pending_text()
        rest = self.port.read_very_eager()
        st = pend_text + rest.decode(self.encoding, errors='replace')
        self._display_raw(st, pend_ts + [time.time()] * len(rest), mute)
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
                # Stamp the byte with its reception time: the display path
                # stamps each log line with the time its first character hit
                # the port, not the time read_until drains it.
                self.rx_queue.put(time.time(), c)

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
            item = self.rx_queue.get(block=timeout >= TIMEOUT_NULL,
                                     timeout=timeout)
            if item is None:
                return None
            data, ts = item
            return data, [ts]

        data = self.port.read(1)
        if not data:
            return None
        return data, [time.time()]

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
            return None
        waiting = self.port.in_waiting
        data = first + (self.port.read(waiting) if waiting else b'')
        return data, [time.time()] * len(data)

    def _push_back(self, data, ts=None):
        if self.bufferize:
            self.rx_queue.pushBack(data, ts)
        else:
            super()._push_back(data, ts)

    def flush(self):
        # Base-class contract: discard everything already received. The
        # previous port.flush() only cleared the OS buffers — with
        # bufferize (the default) the reader thread has already moved the
        # stale bytes into rx_queue, where an OS-level flush never reaches.
        self.read_nowait(mute=True)

    def read_nowait(self, mute=False):
        if not self.isOpened:
            raise ETUMRuntimeError(
                "serial console '{}' ({}) is not open".format(self.name, self.port_id))
        if self.bufferize:
            self._check_reader()
            data, ts = self.rx_queue.getAll()
            st = data.decode(self.encoding, errors='replace')
            self._display_raw(st, ts, mute)
            return st

        pend_text, pend_ts = self._pending_text()
        now = time.time()
        data = self.port.read(self.port.in_waiting)
        st = pend_text + data.decode(self.encoding, errors='replace')
        self._display_raw(st, pend_ts + [now] * len(data), mute)
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
        # The login banner is displayed as it arrives (arrival ≈ read).
        self._display_raw(self.port.read_until("login: ").decode(
            self.encoding, errors='replace'), None, mute=False)
        self.port.write(user + "\n")
        self._display_raw(self.port.read_until("assword").decode(
            self.encoding, errors='replace'), None, mute=False)
        self._display_raw(self.port.read_until(":").decode(
            self.encoding, errors='replace'), None, mute=False)
        self.port.write(pwd + "\n")
        # then connect to the serial port using miniterm console
        self._display_raw(self.port.read_until("~]$" ).decode(
            self.encoding, errors='replace'), None, mute=False)
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

            if not data:
                continue
            # One reception time per byte: the file log and the stream log
            # stamp a line with the time its first character arrived.
            ts = time.time()
            self.rx_queue.put((data, ts))
            data = data.decode(self.encoding, errors='replace')
            # if valid char, write into the file
            if self._is_valid_character(data):
                # replace '\r' by '\n' and '\r\n' by '\n'
                if data == '\r':
                    data = ''
                    continue
                 # date at reception of first new char of the line
                if line_buffer is None:
                    line_buffer = '[' + _stamp_str(ts) + ']'
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
            data, ts = self.rx_queue.get(timeout=timeout)
        except Empty:
            return None
        return data, [ts]

    def read_available(self, timeout):
        first = self.readchar(timeout)
        if first is None:
            return None
        data, ts = first[0], list(first[1])
        try:
            while True:
                d, t = self.rx_queue.get_nowait()
                data += d
                ts.append(t)
        except Empty:
            return data, ts

    def read_nowait(self, mute=False):
        if self.log_fd is None:
            raise ConnectionAbortedError(
                "console '{}' closed while reading".format(self.name))
        chars, ts = self._pending_text()
        for _ in range(self.rx_queue.qsize()):
            d, t = self.rx_queue.get()
            chars += d.decode(self.encoding, errors='replace')
            ts += [t] * len(d)
        self._display_raw(chars, ts, mute)
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
