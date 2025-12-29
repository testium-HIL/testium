import os
import sys
from multiprocessing import Process, Pipe

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.test_items.tested_references_files import tested_refs_dialog
import libs.testium as tm
from interpreter.utils.tum_except import ETUMSyntaxError
from interpreter.utils.constants import TestItemType as cst

class TestItemTestedRefsDialog(TestItem):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_REFERENCE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_REFERENCE_DLG
        self.is_container = False
        try:
            self._question = self._prms.getParam('question', required=True)
            self._init_values = self._prms.getParamAll('reference', required=False, processed=True)
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has a missing or wrong parameter",
                self.seqFilename(),
            )

    @test_run
    def execute(self):
        ourpath=__file__
        test_file=os.path.join(os.path.dirname(ourpath),
                                 'tested_references_files',
                                 'tested_refs_dialog.py')

        q=self._prms.expanse(self._question)
        parent_conn, child_conn=Pipe()
        init_values=','.join(self._init_values)
        p=Process(target=tested_refs_dialog.main,
                    args=([self.name(), q, init_values],
                        child_conn))
        p.start()
        val, succ=parent_conn.recv()
        p.join()

        titems=[]
        if len(val) > 0:
            i = 0
            for sitem in val.split(','):
                titem={}
                telems=sitem.split('/')
                titem['reference']=telems[0]
                titem['revision']=telems[1]
                titem['serial']=telems[2]
                print("Identification:\n" + str(titem))
                titems.append(titem)
                self.result.reported = {'reference_{}'.format(i): titem}
                i = i + 1
        self.result.value = titems
        tm.setgd('tested_items', titems)
        if len(val) > 0:
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

if __name__ == '__main__':
    p=Process(target=test_dialog.main,  args=(['bob', 'bab'],))
    p.start()
    p.join()
