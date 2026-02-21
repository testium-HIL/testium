from multiprocessing import Process, Pipe

from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestResult, TestValue
from interpreter.test_items.dialog_choices_files import choices_dialog
import libs.testium as tm
from lib.tum_except import ETUMSyntaxError
from interpreter.utils.constants import TestItemType as cst


class TestItemChoicesDialog(TestItem):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_CHOICES_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_CHOICES_DLG
        self.is_container = False
        try:
            self._question = self._prms.getParam("question", required=True)
            self._choices = self._prms.getParam("choices", required=True)
            self._default_icon = self._prms.getParam(
                "icon", required=False, default=None
            )
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' (a child of: '{self.parent().name()}') has a missing or wrong parameter",
                self.seqFilename()
            )

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        choices = self._prms.expanse(self._choices)
        icon = self._prms.expanse(self._default_icon)
        parent_conn, child_conn = Pipe()
        p = Process(
            target=choices_dialog.main, args=([self.name(), q, choices, icon], child_conn)
        )
        p.start()
        val, succ = parent_conn.recv()
        p.join()

        self.result.value = val

        if succ:
            # The result of the test item is put into the global dict
            tm.setgd("cs_" + self._name, val)
            self.result.set(TestValue.SUCCESS, str(val))
        else:
            tm.delgd("cs_" + self._name)
            self.result.set(TestValue.FAILURE, str(val))
