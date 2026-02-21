import os
import sys
from multiprocessing import Process, Pipe

from PySide6.QtWidgets import QMessageBox

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.test_items.dialog_question_files import question_dialog
from lib.tum_except import ETUMSyntaxError
from interpreter.utils.constants import TestItemType as cst

class TestItemQuestionDialog(TestItem):
    """dialog_question item usage.
    dialog_question name: Nice question, question: "If OK, press OK, If not, press cancel"
    """
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_QUESTION_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_QUESTION_DLG
        self.is_container = False
        try:
            self._question = self._prms.getParam('question', required = True)
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has a missing or wrong parameter",
                self.seqFilename(),
            )

    @test_run
    def execute(self):
        ourpath = __file__
        test_file = os.path.join(os.path.dirname(ourpath),
                                 'dialog_question_files',
                                 'question_dialog.py')

        q = self._prms.expanse(self._question)
        print('Question asked:\n' + q + '\n')
        parent_conn, child_conn = Pipe()
        p=Process(target=question_dialog.main,
                    args=([self.name(), q],child_conn))
        p.start()
        succ = parent_conn.recv()
        p.join()
        if succ == QMessageBox.Yes:
            self.result.set(TestValue.SUCCESS)
            print('Answer:    YES\n')
        else:
            self.result.set(TestValue.FAILURE)
            print('Answer:    NO\n')

def mypath():
    if hasattr(sys, "frozen"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

from multiprocessing import Process

if __name__=='__main__':
    p=Process(target=test_dialog.main,  args=(['bob', 'bab'],))
    p.start()
    p.join()
