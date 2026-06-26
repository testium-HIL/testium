import sys
import os
import importlib
import traceback

import api.testium as tm
from runtime.tum_except import ETUMSyntaxError, ETUMRuntimeError
from runtime.stdout_redirect import stdio_redir
from interpreter.test_items.test_item import test_run
from interpreter.test_items.item_actions import TestItemActions
from interpreter.test_items.item_actions.action import TestItemAction
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.param_decl import Param, ParamSet
from interpreter.test_items.test_result import TestValue


class TestItemConsoleAction(TestItemAction):

    def console_name(self):
        """Resolve and validate the parent ``console_name``.

        ``required=True`` only enforces key presence, so an empty
        ``console_name:`` (YAML ``None``) or an unresolved ``$(var)`` reaches
        here as ``None``. Raise an explicit ETUMRuntimeError instead of letting
        ``None`` flow into the Console constructor (cryptic ``TypeError`` while
        building the prompt) or into every later action (``NoneType`` cascade).
        """
        cname = self._prms.expanse(self.token["console_name"])
        if not isinstance(cname, str) or cname.strip() == "":
            raise ETUMRuntimeError(
                "'console_name' is missing, empty or unresolved (resolved to "
                f"{cname!r}). Set a non-empty 'console_name' on the 'console' item "
                "'{}' — it is the identifier shared by every nested action "
                "(open/write/writeln/read_until/close).".format(self.parent()._name),
                self.seqFilename(),
            )
        return cname

    def get_console(self):
        cname = self.console_name()
        cons = tm.console(cname)
        if cons is None or not getattr(cons, "isOpened", False):
            raise ETUMRuntimeError(
                f"console '{cname}' is not open: its 'open' action failed, never "
                f"ran, or the console was already closed. An 'open' action for "
                f"console '{cname}' must succeed before this action.",
                self.seqFilename(),
            )
        return cons


class TestItemConsoleOpen(TestItemConsoleAction):

    PARAMS = ParamSet(
        Param("protocol", required=True,
              doc="Transport: 'telnet', 'ssh', 'rawtcp', 'serial' or 'terminal'."),
        Param("write_delay", default=0,
              doc="Inter-character write delay in ms (slow devices)."),
        Param("log", doc="Path to a log file capturing the console traffic."),
        Param("overwrite_log", default=True,
              doc="If true, truncate the log file at open; else append."),
        # telnet
        Param("telnet_host", doc="Hostname/IP for the telnet target."),
        Param("telnet_port", default=69, doc="TCP port for telnet."),
        # ssh
        Param("ssh_host", doc="Hostname/IP for the SSH target."),
        Param("ssh_user", doc="SSH login user."),
        Param("ssh_pwd",  doc="SSH password (if key-based auth is not used)."),
        # rawtcp
        Param("tcp_host", doc="Hostname/IP for a raw-TCP connection."),
        Param("tcp_port", doc="TCP port for a raw-TCP connection."),
        # serial
        Param("serial_port",     doc="Serial device path (e.g. /dev/ttyUSB0 or COM3)."),
        Param("serial_baudrate", doc="Serial baudrate."),
        Param("buffered", default=True,
              doc="If true, the serial console buffers received bytes between reads."),
        # terminal
        Param("terminal_path",
              doc="Working directory for the local terminal protocol."),
        Param("shell",
              doc="Shell command used for the local terminal protocol "
                  "(default: 'cmd.exe' on Windows, '/usr/bin/env bash' elsewhere)."),
    )

    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_CONSOLE_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )
        self._protocol = self._prms.getParam("protocol", required=True)

    @test_run
    def execute(self):
        self._protocol = self._prms.expanse(self._protocol)
        if not (self._protocol in ["telnet", "ssh", "rawtcp", "serial", "terminal"]):
            self.result.set(
                TestValue.FAILURE,
                '"protocol" can only be "telnet", "ssh", "rawtcp", "serial" or "terminal"',
            )
            return

        cname = self._prms.expanse(self.token["console_name"])
        write_delay = (
            self._prms.getParam("write_delay", default=0, processed=True) / 1000.0
        )
        log = self._prms.getParam("log", processed=True)
        erase_log = self._prms.getParam("overwrite_log", default=True, processed=True)

        if self._protocol == "telnet":
            telnet_host = self._prms.getParam(
                "telnet_host", required=True, processed=True
            )
            telnet_port = self._prms.getParam("telnet_port", default=69, processed=True)

        elif self._protocol == "ssh":
            if tm.OS() == "Windows":
                self.result.set(
                    TestValue.FAILURE, "SSH protocol not supported on Windows"
                )
                return
            ssh_host = self._prms.getParam("ssh_host", required=True, processed=True)
            ssh_user = self._prms.getParam("ssh_user", required=True, processed=True)
            ssh_pwd = self._prms.getParam(
                "ssh_pwd", required=False, default=None, processed=True
            )

        elif self._protocol == "rawtcp":
            rawtcp_host = self._prms.getParam("tcp_host", required=True, processed=True)
            rawtcp_port = self._prms.getParam("tcp_port", required=True, processed=True)

        elif self._protocol == "serial":
            serial_port = self._prms.getParam(
                "serial_port", required=True, processed=True
            )
            serial_bauds = self._prms.getParam(
                "serial_baudrate", required=True, processed=True
            )
            buffered = self._prms.getParam(
                "buffered", default=True, required=False, processed=True
            )

        else:
            terminal_path = self._prms.getParam("terminal_path", processed=True)
            if terminal_path is not None:
                terminal_path = os.path.normpath(terminal_path)
            default_shell = "cmd.exe" if tm.OS() == "Windows" else "/usr/bin/env bash"
            terminal_shell = self._prms.getParam(
                "shell", default=default_shell, required=False, processed=True
            )

        try:
            # Validate console_name explicitly (empty/unresolved → clean error,
            # not a cryptic TypeError inside the Console constructor).
            cname = self.console_name()
            if self._protocol == "telnet":
                if log:
                    cons = console.TelnetLoggedConsole(
                        name=cname,
                        host=telnet_host,
                        port=telnet_port,
                        overwriteFile=erase_log,
                        logPath=log,
                        write_delay=write_delay,
                    )
                else:
                    cons = console.TelnetConsole(
                        name=cname,
                        host=telnet_host,
                        port=telnet_port,
                        write_delay=write_delay,
                    )

            elif self._protocol == "ssh":
                if tm.OS() == "Windows":
                    raise ETUMSyntaxError(
                        f"The '{self.cmd()}' test item named '{self.name()}' does not support SSH protocol on Windows",
                        self.seqFilename()
                    )
                if log:
                    tm.print_warn(
                        f"Warning : For '{self.cmd()}' test item named '{self.name()}', logging of {self._protocol} is not yet supported"
                    )
                cons = console_ssh.SshConsole(
                    name=cname,
                    host=ssh_host,
                    user=ssh_user,
                    password=ssh_pwd,
                    echoOn=True,
                )

            elif self._protocol == "rawtcp":
                if log:
                    tm.print_warn(
                        "Warning : logging of {} is not yet supported".format(
                            self._protocol
                        )
                    )
                cons = raw_tcp_console.RawTCPConsole(
                    name=cname,
                    address=rawtcp_host,
                    port=rawtcp_port,
                    echoOn=True,
                    write_delay=write_delay,
                )

            elif self._protocol == "serial":
                if log:
                    cons = console.SerialLoggedConsole(
                        name=cname,
                        baudrate=serial_bauds,
                        port=serial_port,
                        overwriteFile=erase_log,
                        logPath=log,
                        echoOn=False,
                        write_delay=write_delay,
                    )
                else:
                    cons = console.SerialConsole(
                        name=cname,
                        baudrate=int(serial_bauds),
                        port=serial_port,
                        bufferize=bool(buffered),
                        echoOn=False,
                        write_delay=write_delay,
                    )

            else:
                if log:
                    print(
                        "Warning : logging of {} is not yet supported".format(
                            self._protocol
                        )
                    )
                if terminal_path and not os.path.exists(terminal_path):
                    raise ETUMSyntaxError(
                        f"'{self.cmd()}' test item named '{self.name()}' (console '{cname}'): terminal path is not mandatory but must exist when provided: {terminal_path}",
                        self.seqFilename()
                    )
                cons = termconsole.TermConsole(
                    name=cname,
                    project_path=terminal_path,
                    cust_shell=terminal_shell,
                    echoOn=True,
                    write_delay=write_delay,
                )

            cons.stream = stdio_redir.stream
            cons.open()
            # Register only after a successful open: a console whose open failed
            # must stay unreachable so later actions report a clean "not open"
            # error instead of operating on a half-built transport.
            tm.add_console(cons)
            self.result.set(TestValue.SUCCESS)
        except ETUMRuntimeError as e:
            # Expected console error (device missing, no permission…): one line.
            msg = "Impossible to open the console '{}': {}".format(cname, e._message)
            self.result.set(result=TestValue.FAILURE, message=msg)
            print(msg)
        except Exception as e:
            # Unexpected error: keep the full traceback for diagnosis.
            self.result.set(
                result=TestValue.FAILURE,
                message="Impossible to open the console '{}': {}".format(cname, e),
            )
            traceback.print_exception(*sys.exc_info())


class TestItemConsoleClose(TestItemConsoleAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_CONSOLE_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

    @test_run
    def execute(self):
        try:
            cname = self.console_name()
        except ETUMRuntimeError as e:
            self.result.set(result=TestValue.FAILURE, message=e._message)
            print(e._message)
            return
        # Closing a console that was never opened (open failed earlier) is a
        # no-op success, not an error — nothing to release.
        cons = tm.console(cname)
        if cons is not None:
            try:
                cons.close()
                tm.remove_console(cname)
            except Exception:
                pass
        self.result.set(result=TestValue.SUCCESS)


class TestItemConsoleWrite(TestItemConsoleAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_CONSOLE_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

    @test_run
    def execute(self):
        try:
            msg = self._prms.expanse(self._prms.getData())
            cons = self.get_console()
            cons.write(str(msg))
            self.result.set(result=TestValue.SUCCESS)
            self.result.reported = {"data": msg}
        except ETUMRuntimeError as e:
            # Expected console error (e.g. console not open): clear one-liner.
            m = f"Console '{self.token['console_name']}': impossible to write ({e._message})"
            self.result.set(result=TestValue.FAILURE, message=m)
            print(m)
        except Exception:
            print(traceback.format_exc())
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Console '{self.token['console_name']}': impossible to write",
            )


class TestItemConsoleWriteLn(TestItemConsoleAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_CONSOLE_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

    @test_run
    def execute(self):
        try:
            msg = self._prms.expanse(self._prms.getData())
            cons = self.get_console()
            cons.write(str(msg) + "\n")
            self.result.set(result=TestValue.SUCCESS)
            self.result.reported = {"data": msg}
        except ETUMRuntimeError as e:
            # Expected console error (e.g. console not open): clear one-liner.
            m = f"Console '{self.token['console_name']}': impossible to write ({e._message})"
            self.result.set(result=TestValue.FAILURE, message=m)
            print(m)
        except Exception:
            print(traceback.format_exc())
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Console '{self.token['console_name']}': impossible to write",
            )


class TestItemConsoleReadUntil(TestItemConsoleAction):

    PARAMS = ParamSet(
        Param("expected", required=True,
              doc="Literal string — or a list of strings — matched against the "
                  "incoming console output. The read succeeds as soon as one of "
                  "them is seen, or fails on timeout."),
        Param("timeout", default=-1,
              doc="Seconds before giving up. Negative means infinite."),
        Param("mute", default=False,
              doc="If true, don't echo received bytes to testium's stdout/log."),
        Param("regex", default=False,
              doc="If true, each 'expected' entry is treated as a Python "
                  "regular expression (searched, not anchored) instead of a "
                  "literal string."),
    )

    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_CONSOLE_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )
        self._read_until = self._prms.getParam("expected", required=True)

    @test_run
    def execute(self):
        # 'expected' may be a single value or a list of values (match any).
        if isinstance(self._read_until, (list, tuple)):
            ru = [self._prms.expanse(m) for m in self._read_until]
        else:
            ru = self._prms.expanse(self._read_until)
        read_timeout = int(self._prms.getParam("timeout", default=-1, processed=True))
        mute = self._prms.getParam("mute", default=False, processed=True)
        use_regex = self._prms.getParam("regex", default=False, processed=True)
        if read_timeout < 0:
            read_timeout = None

        try:
            cons = self.get_console()
            status, data = cons.read_until(
                ru, timeout=read_timeout, return_data=True, mute=mute,
                should_stop=self.isStopped, regex=bool(use_regex),
            )
            if status == 0:
                self.result.set(TestValue.SUCCESS)
                self.result.value = data
            elif self.isStopped():
                self.result.set(
                    result=TestValue.FAILURE,
                    message="Console read aborted on stop request",
                )
            else:
                self.result.set(result=TestValue.FAILURE, message="No matching text")
            reported = {"data": "" if mute else data}
            # When several patterns were given, expose which one matched.
            if status == 0 and isinstance(ru, (list, tuple)):
                reported["matched"] = getattr(cons, "_matched", None)
            self.result.reported = reported
            # The result is put in global dir
            tm.setgd("cn_" + self.parent()._name, data)

        except ETUMRuntimeError as e:
            # Expected console error (e.g. console not open): clear one-liner.
            msg = f"Console '{self.token['console_name']}': impossible to read ({e._message})"
            self.result.set(result=TestValue.FAILURE, message=msg)
            print(msg)
        except Exception:
            # Unexpected error: keep the full traceback for diagnosis.
            print(traceback.format_exc())
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Console '{self.token['console_name']}': impossible to read",
            )


class TestItemConsole(TestItemActions):

    PARAMS = ParamSet(
        Param("console_name", required=True,
              doc="Identifier of the console — used by every nested action to "
                  "reach back the same transport. Multiple consoles can coexist "
                  "as long as their names differ."),
    )

    ACTIONS = {
        "open": TestItemConsoleOpen,
        "close": TestItemConsoleClose,
        "write": TestItemConsoleWrite,
        "writeln": TestItemConsoleWriteLn,
        "read_until": TestItemConsoleReadUntil,
    }

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(
            cst.TYPE_CONSOLE, dict_item, parent, status_queue, filename=filename
        )

        self.actions_token = {}

        global console
        console = importlib.import_module("api.console")

        if not sys.platform.startswith("win"):
            global console_ssh
            console_ssh = importlib.import_module("api.console_ssh")

        global termconsole
        termconsole = importlib.import_module("api.termconsole")

        global raw_tcp_console
        raw_tcp_console = importlib.import_module("api.raw_tcp_console")

        self.actions_token["console_name"] = self._prms.getParam(
            "console_name", required=True
        )
