import os
import sys

from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
from interpreter.utils.constants import TestItemType as cst
from runtime.tum_except import item_load_context


class TestItemMsgDialog(TestItemDialogBase):
    """dialog_message item usage.
    dialog_message name: Nice message, question: Open the door and press OK
    """
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_MESSAGE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_MESSAGE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam('question', required=True)
            self._auto_result = self._prms.getParam('auto_result', required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        print("Message Displayed:\n" + q)
        if _is_text_mode():
            if _is_interactive():
                input("Press Enter to continue...")
                self.result.set(TestValue.SUCCESS)
            else:
                ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
                if ar is not None:
                    self.result.set(TestValue.SUCCESS)
                else:
                    self.result.set(TestValue.FAILURE, 'Dialog not supported in batch mode')
            return
        from interpreter.test_items.dialog_msg_files import msg_dialog
        ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
        args = [self.name(), q] + ([ar] if ar is not None else [])
        exitcode = self._run_dialog(msg_dialog.main, args)
        if exitcode == 0:
            self.result.set(TestValue.SUCCESS)
        else:
            self.result.set(TestValue.FAILURE, f"Dialog subprocess exited with code {exitcode}")
