import os
import sys
from multiprocessing import Process, Pipe

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.test_items.dialog_note_files import test_dialog
from lib.tum_except import ETUMSyntaxError, item_load_context
import libs.testium as tm
from interpreter.utils.constants import TestItemType as cst

class TestItemNoteDialog(TestItem):
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_NOTE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_NOTE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam('question', required=True)

    @test_run
    def execute(self):
        ourpath = __file__
        test_file = os.path.join(os.path.dirname(ourpath),
                                 'dialog_note_files',
                                 'test_dialog.py')

        q = self._prms.expanse(self._question)
        print("Question:\n" + q)
        parent_conn, child_conn = Pipe()
        p=Process(target=test_dialog.main,  args=([self.name(), q],child_conn))
        p.start()
        val, succ = parent_conn.recv()
        p.join()
        tm.setgd(self.name(), val)
        print("\n" + ("-" * 80) + "\n")
        print("- Test note\n")
        print("-" * 80 + "\n")
        print(val)
        print("-" * 80 + "\n")
        self.result.reported = {'note': val}
        if succ:
            self.result.set(TestValue.SUCCESS, val)
        else:
            self.result.set(TestValue.FAILURE, val)

def mypath():
    if hasattr(sys, "frozen"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

from multiprocessing import Process

if __name__=='__main__':
    p=Process(target=test_dialog.main,  args=(['bob', 'bab'],))
    p.start()
    p.join()
