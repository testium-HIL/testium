import sys
import importlib
import traceback
from functools import wraps

import libs.testium as tm
from lib.tum_except import ETUMSyntaxError, item_load_context
from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestResult, TestValue
from interpreter.test_items.item_actions import TestItemActions
from interpreter.test_items.item_actions.action import TestItemAction
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.eval import evaluate


class TestItemPlotAction(TestItemAction):

    def get_plot(self):
        gname = self._prms.expanse(self.token)
        return gname, tm.plot(gname)


class TestItemPlotActionOpen(TestItemPlotAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_GRAPH_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

        self._log_path = self._prms.getParam("log_path", None, required=False)

    @test_run
    def execute(self):
        try:
            gname = self._prms.expanse(self.token)
            lpath = self._prms.expanse(self._log_path)
            gr = runtime_plot.RuntimePlot(gname, lpath)
            tm.add_plot(gr)

        except Exception as e:
            self.result.set(
                result=TestValue.FAILURE,
                message="Impossible to open the plot ({}) (exception: {})".format(
                    self._plot_name, e
                ),
            )
            traceback.print_exception(*sys.exc_info())
        else:
            self.result.set(result=TestValue.SUCCESS)


class TestItemPlotActionClose(TestItemPlotAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_GRAPH_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

        self._wait_dialog_exit = self._prms.getParam("wait_dialog_exit", False)
        self._timeout = self._prms.getParam("timeout", -1)

    @test_run
    def execute(self):
        gname, gr = self.get_plot()
        wait_exit = self._prms.expanse(self._wait_dialog_exit)
        tmout = self._prms.expanse(self._timeout)
        try:
            if wait_exit:
                gr.close_wait_dialog_exit(tmout)
            else:
                gr.close()
        except Exception as e:
            self.result.set(
                result=TestValue.FAILURE,
                message="Impossible to close the plot ({}) (exception: {})".format(
                    gname, e
                ),
            )
            traceback.print_exception(*sys.exc_info())
        else:
            self.result.set(result=TestValue.SUCCESS)
        tm.remove_plot(gname)


class TestItemPlotActionPeriodic(TestItemPlotAction):
    def __init__(
        self, action_name, dict_item, parent=None, status_queue=None, filename=""
    ):
        super().__init__(
            action_name,
            cst.TYPE_GRAPH_ACTION,
            dict_item,
            parent,
            status_queue,
            filename=filename,
        )

        # Periodic function call
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self.period = self._prms.getParam("period", required=True)
            self.file_name = self._prms.getParam("file", required=True)
            self.func_name = self._prms.getParam("func_name", required=True)
            self.params = self._prms.getParamAll("param")
            self.post_eval = self._prms.getParam("eval", default="")

    @test_run
    def execute(self):
        gname, gr = self.get_plot()
        try:
            file = self._prms.expanse(self.file_name)
            func_name = self._prms.expanse(self.func_name)
            param_list = self._prms.getParamFromList(self.params)
            pl = self._prms.expanse(param_list)
            post_eval = self._prms.expanse(self.post_eval)
            gr.add_periodic(self.period, file, func_name, pl, post_eval)

        except:
            traceback.print_exception(*sys.exc_info())
            self.result.set(
                result=TestValue.FAILURE, message='Unrecoverable "plot" item error'
            )
        else:
            self.result.set(result=TestValue.SUCCESS)


class TestItemPlotActionAdd(TestItemPlotAction):
    def __init__(self, action_name, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(
            action_name, cst.TYPE_GRAPH_ACTION, dict_item, parent, status_queue, filename=filename
        )

    @test_run
    def execute(self):
        gname, gr = self.get_plot()
        input = self._prms.getData()
        data = {}
        if isinstance(input, str):
            input = self._prms.expanse(input)

        if isinstance(input, dict):
            for k, v in input.items():
                v = self._prms.expanse(v)
                _, v = evaluate(v)
                data.update({k: v})

            gr.add(data)

        else:
            self.result.set(
                TestValue.FAILURE,
                f"Plot item ({self._name}) 'add' content must be a dict.",
            )
            return

        self.result.set(result=TestValue.SUCCESS)


class TestItemPlotActionLastValues(TestItemPlotAction):
    def __init__(self, action_name, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(
            action_name, cst.TYPE_GRAPH_ACTION, dict_item, parent, status_queue, filename=filename
        )

    @test_run
    def execute(self):
        gname, gr = self.get_plot()
        test_res = {}
        keys = self._prms.getParam("name", [], processed=True)
        if isinstance(keys, list):
            last_values = gr.last_values()
            for k in keys:
                test_res.update({k: last_values.get(k, None)})
        else:
            self.result.set(
                TestValue.FAILURE,
                f"Plot item ({self._name}) 'name' parameter of 'last_value' action must be a list.",
            )
            return

        tm.setgd("plv_" + gname, test_res)
        self.result.value = test_res
        self.result.set(result=TestValue.SUCCESS)


class TestItemPlotActionExport(TestItemPlotAction):
    def __init__(self, action_name, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(
            action_name, cst.TYPE_GRAPH_ACTION, dict_item, parent, status_queue, filename=filename
        )

        self.file_name = self._prms.getData()
        if not isinstance(self.file_name, str):
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' 'export' parameter must be a file name",
                self.seqFilename()
            )

    @test_run
    def execute(self):
        gname, gr = self.get_plot()
        fn = self._prms.expanse(self.file_name)
        if gr is not None:
            gr.save(fn)
            print(f"Saved '{gname}' plot in '{fn}'")
        self.result.set(result=TestValue.SUCCESS)


class TestItemPlot(TestItemActions):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(
            cst.TYPE_GRAPH, dict_item, parent, status_queue, filename=filename
        )

        self.register_actions(
            open=TestItemPlotActionOpen,
            close=TestItemPlotActionClose,
            periodic=TestItemPlotActionPeriodic,
            add=TestItemPlotActionAdd,
            last_value=TestItemPlotActionLastValues,
            export=TestItemPlotActionExport,
        )

        self.actions_token = self._prms.getParam("plot_name", required=True)

        global runtime_plot
        runtime_plot = importlib.import_module("libs.runtime_plot")
