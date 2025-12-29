import os

import interpreter.test_report.test_report as tr
from interpreter.utils.paths import prepare_file_to_save
import interpreter.utils.constants as cst
import libs.testium as tm


class ReportExport:
    KEY_SUCCESS = 'success'
    KEY_TITLE = 'title'
    KEY_MESSAGE = 'message'
    KEY_DURATION = 'duration'
    KEY_LOG = 'log'
    ROW_TEXTS = [
        ['Test title', KEY_TITLE],
        ['Message', KEY_MESSAGE],
        ['Duration (s)', KEY_DURATION],
        ['Test Result', KEY_SUCCESS]
    ]
    HEADER_TEXTS = {
        'test_file': 'Test file name',
        'test_name': 'Test name',
        'testrun_date': 'Date of the test',
        'testrun_time': 'Time of the test',
        'test_revision': 'Git revision of the test',
        'report_version': 'Report tool version',
    }
    TEXT_INDEX = 0
    KEY_INDEX = 1

    def __init__(self, name, report_db, report_file, pattern, key):
        self.name = name
        self.pattern = pattern
        self._report_file = report_file
        self.key = key
        self._con = report_db
        self.header = {}
        for row in self._con.execute('SELECT * FROM header'):
            self.header.update({row[0]: row[1]})

    def process_tests(self):
        req = 'SELECT * FROM tests '
        lp = len(self.pattern)
        lk = len(self.key)

        # If key or patterns are defined
        # the query is adapted
        if (lp != 0) or (lk != 0):

            req = req + 'WHERE '

            for i in range(lp):
                pat = self.pattern[i]
                req = req + cst.DB_TEST_NAME + ' LIKE '
                req = req + '"' + pat + '" ' + 'OR '

            for i in range(lk):
                k = self.key[i]
                req = req + cst.DB_TEST_KEY + ' LIKE '
                req = req + '"' + k + '" ' + 'OR '

            req = req[:-len('OR ')] + ' '

        req = req + 'ORDER BY ' + cst.DB_TEST_TIMESTAMP_START
        for row in self._con.execute(req):
            self.testsIterate(row)

    def testsIterate(self, row):
        pass

    def rowData(self, row, name):
        return row[tr.TestReport.indexOf(name)]

    def prepareFile(self, file_ext=''):
        self._file_name = prepare_file_to_save(self._report_file, file_ext)

    def extract_info(self, row):
        ret = {}
        ret[self.KEY_SUCCESS] = self.rowData(row, cst.DB_TEST_RESULT)
        ret[self.KEY_MESSAGE] = self.rowData(row, cst.DB_TEST_MESSAGE)
        ret[self.KEY_TITLE] = self.rowData(row, cst.DB_TEST_NAME)
        ret[self.KEY_DURATION] = tm.timestamp_as_sec(self.rowData(
            row, cst.DB_TEST_DURATION))
        log = self.rowData(row, cst.DB_TEST_LOG)
        if (log is None) or (log == ''):
            ret[self.KEY_LOG] = ''
        else:
            ret[self.KEY_LOG] = log

        return ret

    def extract_test(self, row):
        ret = {}
        for key in cst.DB_TEST_FIELDS:
            r = self.rowData(row, key)
            if isinstance(r, bytes):
                r = r.decode()
            ret[key] = r
        return ret