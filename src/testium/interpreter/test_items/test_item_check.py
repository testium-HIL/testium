
from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import TestValue
from runtime.tum_except import ETUMSyntaxError, item_load_context
import api.testium as tm
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.eval import evaluate
from interpreter.utils.param_decl import Param, ParamSet, LIST

class TestItemCheckValue(TestItem):
    """check item usage.
    check usage:{check: {name: check my func output, steps: ['$(pfn_echo) < 5']}}
    """

    PARAMS = ParamSet(
        Param("values", kind=LIST, required=True,
              doc="List of expressions to evaluate. Each is expanded then "
                  "evaluated; non-truthy results fail the check."),
        # 'steps' is intentionally not redeclared here — it's the deprecated
        # alias of 'values' and is already accepted by COMMON_PARAMS for
        # container items. A runtime warning is emitted when 'steps' is used.
    )

    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_CHECK.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_CHECK
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._action_list = self._prms.getParamAll('steps', default=[], required=False)
            if len(self._action_list) > 0:
                tm.print_warn("'steps' argument of check test item is deprecated and is replaced by 'values'")
            self._action_list += self._prms.getParamAll('values', default=[], required=False)
            if len(self._action_list) <= 0:
                raise ETUMSyntaxError(
                    f"Missing required 'values' parameter",
                    self.seqFilename()
                )

    @test_run
    def execute(self):
        if isinstance(self._action_list, str):
            self._action_list = [self._action_list]

        is_success = True
        #test core function
        for v in self._action_list:
            val = self._prms.expanse(v)
            if not isinstance(val, bool):
                self.result.set(TestValue.FAILURE, f"The expanse of '{v}' must result in a boolean, but it resulted in '{val}'")
                return
            if v != val:
                print("Evaluation of '{}' --> {}.".format(v, val))
            if not val:
                is_success = False

        if is_success:
            self.result.set(TestValue.SUCCESS, 'Check passed')
        else:
            self.result.set(TestValue.FAILURE, 'Check failed')
