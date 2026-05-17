import sys
import os
import importlib
import traceback

import api.testium as tm
from runtime.tum_except import ETUMSyntaxError
from runtime.stdout_redirect import stdio_redir
from interpreter.test_items.test_item import test_run
from interpreter.test_items.item_actions import TestItemActions
from interpreter.test_items.item_actions.action import TestItemAction
from interpreter.utils.constants import TestItemType as cst
from interpreter.test_items.test_result import TestResult, TestValue


class TestItemConsoleAction(TestItemAction):

    def get_console(self):
        cname = self._prms.expanse(self.token["console_name"])
        return tm.console(cname)


class TestItemConsoleOpen(TestItemConsoleAction):
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
            telnet_port = self._prms.getParam("telnet_port", default=69)

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
            # record the console instance in the global dict as consolename instance
            # and consolename key entry in the dictionnary if it exists
            tm.add_console(cons)
            cons.open()
            self.result.set(TestValue.SUCCESS)
        except Exception as e:
            self.result.set(
                result=TestValue.FAILURE,
                message="Impossible to open the console ({}) (exception: {})".format(
                    cname, e
                ),
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
        cons = self.get_console()
        try:
            cons.close()
            tm.remove_console(self._prms.expanse(self.token["console_name"]))
        except:
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
        except:
            test_res = TestResult(
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
        except:
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Console '{self.token['console_name']}': impossible to write",
            )


class TestItemConsoleReadUntil(TestItemConsoleAction):
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
        cons = self.get_console()
        ru = self._prms.expanse(self._read_until)
        read_timeout = int(self._prms.getParam("timeout", default=-1, processed=True))
        mute = self._prms.getParam("mute", default=False, processed=True)
        if read_timeout < 0:
            read_timeout = None

        try:
            status, data = cons.read_until(
                ru, timeout=read_timeout, return_data=True, mute=mute,
                should_stop=self.isStopped,
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
            if mute:
                self.result.reported = {"data": ""}
            else:
                self.result.reported = {"data": data}
            # The result is put in global dir
            tm.setgd("cn_" + self.parent()._name, data)

        except:
            print(traceback.format_exc())
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Console '{self.token['console_name']}': impossible to read",
            )


class TestItemConsole(TestItemActions):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(
            cst.TYPE_CONSOLE, dict_item, parent, status_queue, filename=filename
        )

        self.register_actions(
            open=TestItemConsoleOpen,
            close=TestItemConsoleClose,
            write=TestItemConsoleWrite,
            writeln=TestItemConsoleWriteLn,
            read_until=TestItemConsoleReadUntil,
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
