
from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestValue)
from runtime.tum_except import ETUMSyntaxError
from interpreter.utils.constants import TestItemType as cst
from interpreter.test_report.test_report import Export

class TestItemReport(TestItem):
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_REPORT.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_REPORT
        self.is_container = False

        if not 'export' in dict_item:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' needs an 'export' section",
                self.seqFilename()
            )

        self.tum_report = dict_item['export']

    @test_run
    def execute(self):
        self.result.set(TestValue.FAILURE, 'an exception occured during report execution.')

        dict_rep = self._prms.expanse(self.tum_report)
        if not isinstance(dict_rep, list):
            self.result.set(TestValue.FAILURE, 'Report item needs a "report" section')
            return
        rep_name = self._prms.expanse(self._name)

        reports = []
        for exp in dict_rep:
            reports.append(Export(exp))

        success = TestValue.SUCCESS
        for rep in reports:
            try:
                rep.exec(self.report.db_connection, rep_name, no_header=True)
            except Exception as e:
                print(f"Error reporting '{rep.type}': {e}")


        self.result.set(success)
