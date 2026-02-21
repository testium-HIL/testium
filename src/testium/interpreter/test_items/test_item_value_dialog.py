import os
import sys
from multiprocessing import Process, Pipe

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.test_items.dialog_value_files import test_dialog
import libs.testium as tm
from lib.tum_except import ETUMSyntaxError
from interpreter.utils.constants import TestItemType as cst

class TestItemValueDialog(TestItem):
    """dialog_value item usage.
    dialog_value name: Enter value, question: "Which value did you measure?"
    """
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_VALUE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_VALUE_DLG
        self.is_container = False
        try:
            self._question = self._prms.getParam('question', required = True)
            self._default = self._prms.getParam('default', '')
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has a missing or wrong parameter",
                self.seqFilename(),
            )

    @test_run
    def execute(self):
        ourpath = __file__
        test_file = os.path.join(os.path.dirname(ourpath),
                                 'dialog_value_files',
                                 'test_dialog.py')

        q = self._prms.expanse(self._question)
        d = self._prms.expanse(self._default)
        print("Question:\n" + q)
        parent_conn, child_conn = Pipe()
        p=Process(target=test_dialog.main,  args=([self.name(), q, d],child_conn))
        p.start()
        val, succ = parent_conn.recv()
        p.join()
        tm.setgd(self.name(), val)
        print("Answer: " + val)
        if len(val) > 0:
            self.result.reported = {'question': q, 'answer': val}
            self.result.value = val
            if succ:
                self.result.set(TestValue.SUCCESS, val)
            else:
                self.result.set(TestValue.FAILURE, val)
        else:
            self.result.set(TestValue.FAILURE, 'The dialog did not return any value')

def mypath():
    if hasattr(sys, "frozen"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

from multiprocessing import Process

if __name__=='__main__':
    p=Process(target=test_dialog.main,  args=(['bob', 'bab'],))
    p.start()
    p.join()
