
from lxml import (etree, html)
import interpreter.test_report.report_export as rpe
import interpreter.test_report.test_report as tr
import interpreter.utils.constants as cst

class ReportExportHTML(rpe.ReportExport):

    def __init__(self, name, report_db, report_file, pattern, key, no_header=False):
        super().__init__(name, report_db, report_file, pattern, key)

        self.prepareFile()
        self.create_base()
        self.process_tests()
        with open(self._file_name, 'w') as f:
            f.write(html.tostring(self.root, pretty_print=True).decode())

    def testsIterate(self, row):
        super().testsIterate(row)
        rdata = self.extract_info(row)
        trow = etree.SubElement(self.table, 'tr')
        for r in self.ROW_TEXTS:
            rh = etree.SubElement(trow, 'td')
            if r[self.KEY_INDEX] == self.KEY_DURATION:
                rh.text = '{:.4f}'.format(rdata[r[self.KEY_INDEX]])
            else:
                rh.text = rdata[r[self.KEY_INDEX]]

        if rdata[self.KEY_LOG] != '':
            h2 = etree.SubElement(self.logsection, 'h3')
            h2.text = rdata[self.KEY_TITLE]
            for l in rdata[self.KEY_LOG].splitlines():
                p = etree.SubElement(self.logsection, 'p')
                p.text = l

    def create_base(self):
        repname = self.header[cst.DB_TEST_SET_NAME]
        if self.name != '':
            repname = self.name

        self.root = etree.Element('html', lang='en')
        head = etree.SubElement(self.root, 'head')
        title = etree.SubElement(head, 'title')
        title.text = repname
        self.body = etree.SubElement(self.root, 'body')
        h1 = etree.SubElement(self.body, 'h1')
        h1.text = repname

        div = etree.SubElement(self.body, 'div')
        h2 = etree.SubElement(div, 'h2')
        h2.text = 'Test conditions'

        for k in self.HEADER_TEXTS.keys():
            if k in self.header.keys():
                h = etree.SubElement(div, 'h3')
                h.text = self.HEADER_TEXTS[k]
                p = etree.SubElement(div, 'p')
                p.text = self.header[k]

        div = etree.SubElement(self.body, 'div')
        h2 = etree.SubElement(div, 'h2')
        h2.text = 'Test results'

        self.table = etree.SubElement(self.body, 'table')
        row = etree.SubElement(self.table, 'tr')
        for r in self.ROW_TEXTS:
            rh = etree.SubElement(row, 'th')
            rh.text = r[self.TEXT_INDEX]

        self.logsection = etree.SubElement(self.body, 'div')
        h2 = etree.SubElement(self.logsection, 'h2')
        h2.text = 'Logs'
