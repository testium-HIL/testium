from junit_xml import (TestSuite, TestCase)
import api.testium as tm
from runtime.testium_report import Exporter
import interpreter.utils.constants as cst


class ReportExportJUnit(Exporter):

    def export(self):
        self.test_cases = []
        repname = self.report.header[cst.DB_TEST_SET_NAME]
        if self.name != '':
            repname = self.name
        for row in self.rows:
            self.add_case(row)

        ts = TestSuite(repname, test_cases=self.test_cases,
                       hostname=tm.gd('host_ip'))
        with open(self.out_path, 'w', encoding="utf-8") as f:
            TestSuite.to_file(f, [ts])

    def add_case(self, row):
        log = row.log or ''
        if log == '':
            log = row.message
        try:
            tc = TestCase(row.name, elapsed_sec=row.duration_s,
                        log=log, status=row.result)
        # Workaround for old versions of os.
        except TypeError:
            tc = TestCase(row.name, elapsed_sec=row.duration_s, stdout=log)
        if row.failed:
            m = row.message
            if m == '':
                m = 'test failure'
            tc.add_failure_info(output=m)
        elif row.skipped:
            tc.add_skipped_info('test skipped')
        self.test_cases.append(tc)
