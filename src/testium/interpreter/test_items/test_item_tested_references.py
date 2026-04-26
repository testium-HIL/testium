from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import item_load_context
import libs.testium as tm


class TestItemTestedRefsDialog(TestItemDialogBase):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_REFERENCE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_REFERENCE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam('question', required=True)
            self._init_values = self._prms.getParamAll('reference', required=False, processed=True)
            self._auto_result = self._prms.getParam('auto_result', required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        init_values = ','.join(self._init_values)
        if _is_text_mode():
            print(f"References: {q}")
            rows = init_values.split(',') if init_values else ['']
            result_rows = []
            for i, row in enumerate(rows):
                parts = (row.split('/') + ['', '', ''])[:3]
                if _is_interactive():
                    ref = input(f"Row {i+1} - Reference [{parts[0]}]: ").strip() or parts[0]
                    rev = input(f"Row {i+1} - Revision  [{parts[1]}]: ").strip() or parts[1]
                    serial = input(f"Row {i+1} - Serial    [{parts[2]}]: ").strip() or parts[2]
                else:
                    ref, rev, serial = parts[0], parts[1], parts[2]
                result_rows.append(f"{ref}/{rev}/{serial}")
            val = ','.join(result_rows)
            if _is_interactive():
                succ = True
            else:
                ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
                if ar is None:
                    self.result.set(TestValue.FAILURE, 'Dialog not supported in batch mode')
                    return
                succ = ar != 'cancel'
            result = [val, succ]
        else:
            from interpreter.test_items.tested_references_files import tested_refs_dialog
            ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
            args = [self.name(), q, init_values] + ([ar] if ar is not None else [])
            result = self._run_dialog_with_result(tested_refs_dialog.main, args)
        if result is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
            return
        val, succ = result

        titems = []
        if len(val) > 0:
            i = 0
            for sitem in val.split(','):
                titem = {}
                telems = sitem.split('/')
                titem['reference'] = telems[0]
                titem['revision'] = telems[1]
                titem['serial'] = telems[2]
                print("Identification:\n" + str(titem))
                titems.append(titem)
                self.result.reported = {'reference_{}'.format(i): titem}
                i += 1
        self.result.value = titems
        tm.setgd('tested_items', titems)
        if len(val) > 0:
            if succ:
                self.result.set(TestValue.SUCCESS, val)
            else:
                self.result.set(TestValue.FAILURE, val)
        else:
            self.result.set(TestValue.FAILURE, 'The dialog did not return any value')
