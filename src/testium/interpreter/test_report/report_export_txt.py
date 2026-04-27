
from interpreter.test_items.test_result import (TestValue)
import interpreter.test_report.report_export as rpe
import interpreter.test_report.test_report as tr
from interpreter.test_report.report_interface import (adapt_json, convert_json)
from interpreter.utils.constants import TestItemType as cst_type
import interpreter.utils.constants as cst

class ReportExportTxt(rpe.ReportExport):
    no_value_types = [cst_type.TYPE_CONSOLE.item_name, cst_type.TYPE_SLEEP.item_name,
        cst_type.TYPE_IMAGE_DLG.item_name, cst_type.TYPE_LET.item_name, cst_type.TYPE_CHECK,
        cst_type.TYPE_CYCLE.item_name, cst_type.TYPE_GROUP.item_name,
        cst_type.TYPE_UNITTEST.item_name, cst_type.TYPE_MESSAGE_DLG.item_name,
        cst_type.TYPE_QUESTION_DLG.item_name]

    def __init__(self, name, report_db, report_file, pattern, key, no_header=False):
        super().__init__(name, report_db, report_file, pattern, key)

        self.prepareFile()
        self._file_descriptor = open(self._file_name, 'w', encoding="utf-8")

        if not no_header:
            self.write_header()
        self.process_tests()
        self.write_footer()

        self._file_descriptor.close()

    def testsIterate(self, row):
        super().testsIterate(row)
        level = self.rowData(row, cst.DB_TEST_LEVEL)
        if level > 0:
            succ = self.rowData(row, cst.DB_TEST_RESULT)
            msg = self.rowData(row, cst.DB_TEST_MESSAGE)
            tiname = self.rowData(row, cst.DB_TEST_NAME)
            j = self.rowData(row, cst.DB_TEST_DATA)
            if succ == str(TestValue.SUCCESS):
                msg = ''
            if succ != str(TestValue.NORUN):
                self.line_result(tiname, succ, msg, level)

            ty = self.rowData(row, cst.DB_TEST_TYPE)
            if ty in self.no_value_types:
                pass
            else:
                if isinstance(j, bytes):
                    j = convert_json(j)
                if isinstance(j, dict):
                    for k, v in j.items():
                        self.line_value(tiname, k, '=', v, level)

    def addtxt(self, str):
        self._file_descriptor.write(str)

    def separator(self):
        self.addtxt('=' * 60 + '\n')

    def banner(self, level):
        if level <= 0:
            b = '='
        elif level == 1:
            b = '-'
        else:
            b = '- '

        sstart = self.line_start(0)
        line = sstart + b * int((60 - len(sstart))/len(b))
        self.addtxt(line  + '\n')

    def write_header(self):
        repname = self.header[cst.DB_TEST_SET_NAME]
        if self.name != '':
            repname = self.name
        self.addtxt('Testium' + '\n')
        self.addtxt('{:^96}'.format(repname)+'\n')
        self.addtxt('{:^96}'.format(
            self.header[cst.DB_TESTRUN_DATE] + ' ' +
            self.header[cst.DB_TESTRUN_TIME]) + '\n\n\n')

    def write_footer(self):

        self.separator()
        self.addtxt('\n')
        succ = 'Not finished'
        if cst.DB_TEST_SET_RESULT in self.header:
            succ = self.header[cst.DB_TEST_SET_RESULT]

        self.addtxt('{:<40}'.format('Overall test status')
                    + '{:>55}'.format(succ) + '\n\n\n')

        self.addtxt('{:<40}'.format('Operator:')
                        + '{:<40}'.format('signature:') + '\n\n\n')

    def line_text(self, text, level):
        self.addtxt('{:.<45}'.format(self.line_start(level))
                         + ': ' + text + '\n')

    def line_begin(self, ti_name):
        sstart = self.line_start(0) + ' ' + ti_name
        self.addtxt('{:.<45}'.format(sstart) + ': test Begins' + '\n')

    def line_result(self, ti_name, tresult, tmessage, level):
        sstart = ''
        if len(self.pattern) == 0:
            sstart = self.line_start(level) + ' '
        sstart = sstart + ti_name

        if tresult == str(TestValue.SUCCESS) or tresult == str(TestValue.FAILURE):
            self.addtxt('{:.<45}'.format(sstart)
                            + ': {:<43}{:>5}'.format(tmessage,
                                                    tresult) + '\n')

    def line_value(self, title, key, sep, value, level):
        sstart = ''
        if len(self.pattern) == 0:
            sstart = self.line_start(level) + ' '
        sstart = '{:.<45}'.format(sstart + '  ' + title)
        self.addtxt('{:}: {:} {:} {:}'.format(sstart,
                                              str(key),
                                              str(sep),
                                              str(value)) + '\n')

    def line_start(self, level):
        sstart = ''
        pat = '   |'
        sstart = pat * (level-1)
        return sstart
