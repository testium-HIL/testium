from junit_xml import (TestSuite, TestCase)
import libs.testium as tm
from interpreter.test_items.test_result import (TestValue)
import interpreter.test_report.report_export as rpe
import interpreter.test_report.test_report as tr
import interpreter.utils.constants as cst


class ReportExportJUnit(rpe.ReportExport):

    def __init__(self, name, report_db, report_file, pattern, key, no_header=False):
        super().__init__(name, report_db, report_file, pattern, key)

        self.prepareFile()
        self.test_cases = []
        repname = self.header[cst.DB_TEST_SET_NAME]
        if self.name != '':
            repname = self.name
        self.process_tests()

        ts = TestSuite(repname, test_cases=self.test_cases,
                       hostname=tm.gd('host_ip'))
        with open(self._file_name, 'w') as f:
            TestSuite.to_file(f, [ts])

    def testsIterate(self, row):
        super().testsIterate(row)
        rdata = self.extract_info(row)
        log = rdata[self.KEY_LOG]
        if log == '':
            log = rdata[self.KEY_MESSAGE]
        try:
            tc = TestCase(rdata[self.KEY_TITLE], elapsed_sec=rdata[self.KEY_DURATION],
                        log=log, status=rdata[self.KEY_SUCCESS])
        # Workaround for old versions of os.
        except TypeError:
            tc = TestCase(rdata[self.KEY_TITLE], elapsed_sec=rdata[self.KEY_DURATION], stdout=log)
        if rdata[self.KEY_SUCCESS] == str(TestValue.FAILURE):
            m = rdata[self.KEY_MESSAGE]
            if m == '':
                m = 'test failure'
            tc.add_failure_info(output=m)
        elif rdata[self.KEY_SUCCESS] == str(TestValue.NORUN):
            tc.add_skipped_info('test skipped')
        self.test_cases.append(tc)
