
from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import TestValue
from interpreter.utils.tum_except import ETUMSyntaxError
import libs.testium as tm
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.eval import evaluate

class TestItemCheckValue(TestItem):
    """check item usage.
    check usage:{check: {name: check my func output, steps: ['$(pfn_echo) < 5']}}
    """
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_CHECK.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_CHECK
        self.is_container = False
        try:
            self._action_list = self._prms.getParamAll('steps', default=[], required=False)
            if len(self._action_list) > 0:
                tm.print_warn("'steps' argument of check test item is deprecated and is replaced by 'values'")
            self._action_list += self._prms.getParamAll('values', default=[], required=False)
            if len(self._action_list) <= 0:
                raise ETUMSyntaxError(
                    f" The '{self.cmd()}' test item named '{self.name()}' must have a 'values' parameter",
                    self.seqFilename()
                )
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' (a child of: '{self.parent().name()}') has a missing or wrong parameter",
                self.seqFilename(),
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
