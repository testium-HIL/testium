import json
import interpreter.test_report.report_export as rpe
import interpreter.utils.constants as cst


class ReportExportJSON(rpe.ReportExport):

    def __init__(self, name, report_db, report_file, pattern, key, no_header=False):
        super().__init__(name, report_db, report_file, pattern, key)

        self._no_header = no_header
        self._tests = []
        self.prepareFile()
        self.process_tests()
        if no_header:
            if self.name != "":
                json_export = {self.name: self._tests}
        else:
            tests_name = "tests"
            if self.name != "":
                tests_name = self.name
            json_export = {"header": self.header}
            json_export.update({tests_name: self._tests})
        with open(self._file_name, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(json_export, indent=4))

    def testsIterate(self, row):
        super().testsIterate(row)
        r = self.extract_test(row)
        if r[cst.DB_TEST_DATA].strip().startswith("{"):
            r[cst.DB_TEST_DATA] = json.loads(r[cst.DB_TEST_DATA])
        self._tests.append(r)
