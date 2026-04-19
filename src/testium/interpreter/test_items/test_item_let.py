import random
import os
import sys
import time

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from lib.tum_except import ETUMSyntaxError, item_load_context
import libs.testium as tm
from interpreter.utils.constants import TestItemType as cst

class TestItemLet(TestItem):
    """let item usage.
    let values: {variable1: a, variable2: /dev/ttyUSB0, variable3: 115200}
    let eval: {conditional_exec: "random.randint(1, 4)"}
    """
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_LET.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_LET
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._values_list = self._prms.getParamAll('values', default=[], required=False)
            if len(self._values_list) <= 0:
                raise ETUMSyntaxError(
                    f"Missing required 'values' parameter",
                    self.seqFilename(),
                )

    @test_run
    def execute(self):
        if isinstance(self._values_list, dict):
            l = []
            for k in self._values_list.keys():
                l.append({k: self._values_list[k]})
            self._values_list = l
        #test core function
        for i in self._values_list:
            for k, v in i.items():
                key = self._prms.expanse(k)
                ev = self._prms.expanse(v)
                tm.setgd(key, ev)
                self.result.reported = {key: ev}
                print('global value "{}" set to "{}"'.format(key, ev))

        self.result.set(TestValue.SUCCESS, 'Variable set')
