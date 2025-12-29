import os
import sys
from multiprocessing import Process, Pipe

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestValue)
from interpreter.test_items.dialog_msg_files import msg_dialog
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.tum_except import ETUMSyntaxError

class TestItemMsgDialog(TestItem):
    """dialog_message item usage.
    dialog_message name: Nice message, question: Open the door and press OK
    """
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_MESSAGE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_MESSAGE_DLG
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
                                 'dialog_msg_files',
                                 'msg_dialog.py')

        q = self._prms.expanse(self._question)
        print("Message Displayed:\n" + q)
        parent_conn, child_conn = Pipe()
        p=Process(target=msg_dialog.main,
                    args=([self.name(), q],))
        p.start()
        p.join()
        self.result.set(TestValue.SUCCESS)

def mypath():
    if hasattr(sys, "frozen"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

from multiprocessing import Process

if __name__=='__main__':
    p=Process(target=msg_dialog.main,  args=(['bob', 'bab'],))
    p.start()
    p.join()
