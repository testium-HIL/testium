import json
import socket
import re
import struct

from interpreter.utils.tum_except import ETUMRuntimeError
import libs.testium as tm
from libs.console import Console


def is_ip_address(address):
    ip_regex = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    return re.match(ip_regex, address) is not None


def is_ip_multicast(ip):
    # convert the IP as an integer
    ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
    # Checks if it is in a multicast range
    return 0xE0000000 <= ip_int <= 0xEFFFFFFF


def jrpc_query(version: str, method: str, obj, jrpc_id: int):
    req = {
        "1.0": {
            "method": method,
        },
        "2.0": {
            "jsonrpc": "2.0",
            "method": method,
        },
    }
    if not version in ["1.0", "2.0"]:
        raise ETUMRuntimeError("JSONRPC frame creation with bad version value.")
    req = req[version]
    req["params"] = obj
    req["id"] = jrpc_id
    return json.dumps(req)


class JrpcAdapter:
    """Base class for defining a JSONRPC messages handler for the jsonrpc test item."""

    def __init__(self, timeout: float = 1.0, version="1.0", mute=False) -> None:
        self._jrpc_version = version
        self._mute = mute
        self._timeout = timeout
        if not (version == "1.0" or version == "2.0"):
            raise ETUMRuntimeError("Invalid JSONRPC version passed.")

    @property
    def timeout(self):
        return self._timeout

    def check_answer(self, obj, jrpc_id: int) -> None:
        if "1.0" == self._jrpc_version:
            if not ("error" in obj.keys()):
                raise ETUMRuntimeError(
                    "Malformed JSONRPC 1.0 answer. 'error' required."
                )
            if not ("result" in obj.keys()):
                raise ETUMRuntimeError(
                    "Malformed JSONRPC 1.0 answer. 'result' required."
                )

            if obj["result"] is not None and obj["error"] is not None:
                raise ETUMRuntimeError(
                    "Malformed JSONRPC 1.0 answer. If 'result' is not null, 'error' must be null."
                )

            if not ("id" in obj.keys()):
                raise ETUMRuntimeError(
                    "Malformed JSONRPC 1.0 answer. 'id' must be defined."
                )
        else:
            if "2.0" != obj.get("jsonrpc", ""):
                raise ETUMRuntimeError(
                    "Malformed JSONRPC 2.0 answer. 'jsonrpc' required."
                )

            is_error = True
            is_result = True
            if not ("error" in obj.keys()):
                is_error = False
            if not ("result" in obj.keys()):
                is_result = False

            if not (is_error ^ is_result):
                raise ETUMRuntimeError(
                    "Malformed JSONRPC 2.0 answer. 'result' and 'result' can't exist together."
                )

        if not ("id" in obj.keys()):
            raise ETUMRuntimeError("The JSONRPC answer 'id' must be defined.")
        if obj["id"] != jrpc_id:
            raise ETUMRuntimeError(
                "The JSONRPC answer ID does not correspond to the request"
            )

    def _build_query(self, method: str, obj, jrpc_id: int):
        return jrpc_query(self._jrpc_version, method, obj, jrpc_id)

    def _send(self, message: str):
        pass

    def _receive(self, timeout: float) -> str:
        pass

    def _open(self):
        pass

    def _close(self):
        pass

    def query(
        self,
        method: str,
        obj,
        jrpc_id="rand",
        send_only: bool = False,
        timeout: float = None,
    ):
        """This performs a jsonrpc query to a jsonrpc server.
        The returned value is a tuple of size 2:
            success, data

        if send_only is true, the function returns immediately after sending the request.
            None is returned.

        if timeout is None:
            the inherited timeout is used.

        if timeout <= 0:
            If the response does not come before the end of the timeout, it fails with an exception.
            if the id doesn't match, an exception is raised.
            success depends on content of the jsonrpc response.
            data is the error code if the success if false, otherwise it is the returned value.

        if timeout > 0:
            If the response does not come before the end of the timeout, it fails with an exception.
            success depends on content of the jsonrpc response.
            data is the error code if the success if false, otherwise it is the returned value.
        """
        tmout = self._timeout if timeout is None else timeout
        self._send(self._build_query(method, obj, jrpc_id))
        if not send_only:
            return self.receive(jrpc_id, tmout)
        else:
            return None, None

    def receive(self, jrpc_id: int, timeout: float = None) -> tuple:
        """This function only receives an answer from a jsonrpc request.
        The values returned are :
           success, data

        if timeout is None:
            the inherited timeout is used.

        if timeout <= 0:
            if no data is available on the port/console, an exception is raised.
            if the id doesn't match, an exception is raised.
            success depends on content of the jsonrpc response.
            data is the error code if the success if false, otherwise it is the returned value.

        if timeout > 0:
            If the response does not come before the end of the timeout, it fails with an exception.
            success depends on content of the jsonrpc response.
            data is the error code if the success if false, otherwise it is the returned value.

        """
        tmout = self._timeout if timeout is None else timeout
        obj = json.loads(self._receive(tmout))
        self.check_answer(obj, jrpc_id)

        if self._jrpc_version == "1.0":
            success = obj["error"] is None
        else:
            success = not obj.get("error", None) is None
        if success:
            data = obj["result"]
        else:
            data = obj["error"]

        return success, data

    def open(self):
        self._open()

    def close(self):
        self._close()


class JrpcUdpAdapter(JrpcAdapter):
    description = "JSONRPC UDP adapter"

    def __init__(
        self,
        server: str,
        snd_port: int = -1,
        rcv_port: int = -1,
        bufsize: int = 1450,
        timeout: float = 1.0,
        version: str = "1.0",
        mute: bool = False,
    ) -> None:
        """server: hostname or ip of the UDP server to which we'll send requests.
        snd_port: port to which we'll send requests.
        rcv_port: port on which we'll wait for responses.
        bufsize: max size of the data to receive
        version: jsonrpc version
        """
        super().__init__(timeout, version, mute)
        self._bufsize = bufsize
        self._server = server
        self._multicast = False
        self._rcv_port = rcv_port
        self._snd_port = snd_port

    @property
    def sock(self):
        return tm.gd(f"jrpc_udp_rcv_port_{self._rcv_port}")

    @sock.setter
    def sock(self, s):
        tm.setgd(f"jrpc_udp_rcv_port_{self._rcv_port}", s)

    def del_global_sock(self):
        tm.delgd(f"jrpc_udp_rcv_port_{self._rcv_port}")

    def _send(self, message: str):

        # gets the address from the hostname if necessary
        srv = (self._server, self._snd_port)
        if not is_ip_address(self._server):
            try:
                socket.gethostbyname(self._server)
                addrinfo = socket.getaddrinfo(
                    self._server, self._snd_port, socket.AF_INET, socket.SOCK_DGRAM
                )
                srv = addrinfo[0][4]
            except socket.gaierror as e:
                raise ETUMRuntimeError("JSONRPC udp send unknown address.")

        # Sends the message to the server
        self.sock.sendto(message.encode(), srv)

        # Don't log if mute
        if not self._mute:
            print(f"  | sent to @{self._server}:{self._snd_port}")

    def _receive(self, timeout: float) -> str:

        # configures the reception timeout
        self.sock.settimeout(timeout)

        # Receives the answer from the server
        try:
            data, addr = self.sock.recvfrom(self._bufsize)

            # In case of buffer overload we chose to complain
            if len(data) >= self._bufsize:
                raise ETUMRuntimeError(
                    "JSONRPC udp answer size overflow. Try to increase the bufsize"
                )

            # Converts binary to string
            res = data.decode()

            # Don't log if mute
            if not self._mute:
                print(f"  | UDP answer: '{res}'")
                print(f"  | received from @{addr[0]}:{addr[1]}")

        except socket.timeout:
            raise ETUMRuntimeError(
                "JSONRPC udp answer took too long. Try to increase the timeout."
            )
        return res

    def _build_query(self, method: str, obj, jrpc_id: int):
        # Overload of the super build query to allow display of the sent message
        message = super()._build_query(method, obj, jrpc_id)
        print(f"  | UDP query: '{message}'")
        return message

    def _open(self):
        # Complain if the socket already exists
        if not tm.gd(f"jrpc_udp_rcv_port_{self._rcv_port}") is None:
            raise ETUMRuntimeError(
                f"A unclosed socket exists for the current reception port ({self._rcv_port})"
            )

        if is_ip_address(self._server) and is_ip_multicast(self._server):
            self._multicast = True

        # Creates the socket and bind to the reception port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        if self._multicast:
            ttl = struct.pack("b", 1)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        self.sock.settimeout(self.timeout)
        self.sock.bind(("", self._rcv_port))

    def _close(self):

        try:
            self.sock.close()
        except:
            pass
        self.del_global_sock()


class JrpcConsoleAdapter(JrpcAdapter):
    description = "JSONRPC console adapter"

    def __init__(
        self,
        cons_name: str,
        endswith: str = "\n",
        timeout: float = 1.0,
        version: str = "1.0",
        mute: bool = False,
    ) -> None:
        """ """
        super().__init__(timeout, version, mute)
        self._endswith = endswith
        self._json_regexp = re.compile(r"^\s*{", re.MULTILINE)

        # if the console is not defined in global we complain
        self._cons = tm.console(cons_name)
        if self._cons is None:
            raise ETUMRuntimeError(
                f"The '{cons_name}' console can't be found in global directory."
            )

    def _send(self, message: str):
        self._cons.write(message + "\n")

    def _receive(self, timeout: float) -> str:
        status, data = self._cons.read_until(
            self._endswith, timeout, return_data=True, mute=self._mute
        )

        # if we did not receive anything, we complain
        if not status == 0:
            raise ETUMRuntimeError(
                f"The '{self._cons.name}' console did not answer in the requested time."
            )

        res = list(self._json_regexp.finditer(data))
        if len(res) <= 0:
            raise ETUMRuntimeError("Not found JSON '^{'")

        return data[res[-1].start() : -len(self._endswith)]
