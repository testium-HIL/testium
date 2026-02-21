import sys
import traceback
from random import randint

from lib.tum_except import ETUMSyntaxError
from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestResult, TestValue

from interpreter.test_items.item_actions import TestItemActions
from interpreter.test_items.item_actions.action import TestItemAction

from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.eval import evaluate

from interpreter.test_items.test_item_json_rpc.jsonrpc_adapters import (
    JrpcAdapter,
    JrpcConsoleAdapter,
    JrpcUdpAdapter,
)


class TestItemJSRPCActionOpen(TestItemAction):

    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_JSON_RPC_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

    @test_run
    def execute(self):
        try:
            self.token.open()
        except Exception as e:
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Error while performing the JSONRPC '{self._name}' action (exception: {e})",
            )
            traceback.print_exception(*sys.exc_info())
        else:
            self.result.set(result=TestValue.SUCCESS)


class TestItemJSRPCActionClose(TestItemAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_JSON_RPC_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

    @test_run
    def execute(self):
        try:
            self.token.close()
        except Exception as e:
            test_res = TestResult(
                result=TestValue.FAILURE,
                message=f"Error while performing the JSONRPC '{self._name}' action (exception: {e})",
            )
            traceback.print_exception(*sys.exc_info())
        else:
            self.result.set(result=TestValue.SUCCESS)


class TestItemJSRPCActionQuery(TestItemAction):

    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_JSON_RPC_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

        self._meth = self._prms.getParam("method", required=True)
        self._obj = self._prms.getParam("params", required=False)
        if self._obj is None:
            self._obj = list()
        self._jrpc_id = self._prms.getParam("id", required=False, default="rand")
        self._send_only = self._prms.getParam("no_wait", required=False, default=False)
        self._timeout = self._prms.getParam("timeout", required=False, default=None)

    @test_run
    def execute(self):
        meth = self._prms.expanse(self._meth)
        obj = self._prms.expanse(self._obj)
        jrpc_id = self._prms.expanse(self._jrpc_id)
        if isinstance(jrpc_id, str) and jrpc_id.lower().startswith("rand"):
            jrpc_id = randint(1, (2**32) - 1)
        send_only = self._prms.expanse(self._send_only)
        timeout = self._prms.expanse(self._timeout)
        try:
            success, result = self.token.query(
                meth, obj, jrpc_id, send_only, timeout=timeout
            )
        except Exception as e:
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Error while performing the JSONRPC '{self._name}' action (exception: {e})",
            )
            traceback.print_exception(*sys.exc_info())
        else:
            # in case the action returned without error, we
            # set the test result value to the data returned by the action.
            if not self._send_only:
                self.result.value = result
            if self._send_only or success:
                self.result.set(result=TestValue.SUCCESS)
            else:
                self.result.set(result=TestValue.FAILURE, message=str(result))


class TestItemJSRPCActionReceive(TestItemAction):

    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_JSON_RPC_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )
        self._timeout = self._prms.getParam("timeout", required=False, default=None)
        self._jrpc_id = self._prms.getParam("id", required=True)

    @test_run
    def execute(self):
        timeout = self._prms.expanse(self._timeout)
        jrpc_id = self._prms.expanse(self._jrpc_id)

        try:
            success, result = self.token.receive(jrpc_id, timeout)
        except Exception as e:
            self.result.set(
                result=TestValue.FAILURE,
                message=f"Error while performing the JSONRPC '{self._name}' action (exception: {e})",
            )
            traceback.print_exception(*sys.exc_info())
        else:
            # in case the action returned without error, we
            # set the test result value to the data returned by the action.
            self.result.value = result
            if success:
                self.result.set(result=TestValue.SUCCESS)
            else:
                self.result.set(result=TestValue.FAILURE, message=str(result))


class TestItemJSON_RPC(TestItemActions):
    """
    This item TBD
    """

    def __init__(
        self, dict_item: dict, parent: TestItem = None, status_queue=None, filename=""
    ):
        super().__init__(
            cst.TYPE_JSON_RPC, dict_item, parent, status_queue, filename=filename
        )

        self.register_actions(
            open=TestItemJSRPCActionOpen,
            close=TestItemJSRPCActionClose,
            query=TestItemJSRPCActionQuery,
            receive=TestItemJSRPCActionReceive,
        )

        # Console specific params
        self._console = self._prms.getParam("console", required=False)
        # UDP specific params
        self._udp = self._prms.getParam("udp", required=False)
        # Common params
        self._jrpc_version = self._prms.getParam(
            "version", required=False, default="1.0"
        )
        self._timeout = self._prms.getParam("timeout", required=True)
        self._mute = self._prms.getParam("mute", required=False, default=False)

        if (self._console is None) and (self._udp is None):
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' must have a 'console' or 'udp' parameter",
                self.seqFilename(),
            )

        self._is_console = False
        if not self._console is None:
            self._is_console = True

    def run_before_test(self):
        jrpc_version = self._prms.expanse(self._jrpc_version)
        mute = self._prms.expanse(self._mute)
        timeout = self._prms.expanse(self._timeout)
        if self._is_console:
            console = self._prms.expanse(self._console)
            console_name = console.get("name")
            console_prompt = console.get("prompt", "\n")
            if console_name is None:
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' 'console' configuration needs member 'name' defined",
                    self.seqFilename(),
                )
            jrpc_adapter = JrpcConsoleAdapter(
                console_name, console_prompt, timeout, jrpc_version, mute
            )
        else:
            udp = self._prms.expanse(self._udp)
            if udp is None or not isinstance(udp, dict):
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' UDP configuration needs 'udp' parameters define",
                    self.seqFilename(),
                )

            server = udp.get("server")
            snd_port = udp.get("snd_port")
            rcv_port = udp.get("rcv_port")
            bufsize = udp.get("bufsize", 1450)
            if server is None or snd_port is None or rcv_port is None:
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' UDP configuration needs 'server', 'snd_port' and 'rcv_port' defined",
                    self.seqFilename(),
                )
            jrpc_adapter = JrpcUdpAdapter(
                server, snd_port, rcv_port, bufsize, timeout, jrpc_version, mute
            )

        self.actions_token = jrpc_adapter
