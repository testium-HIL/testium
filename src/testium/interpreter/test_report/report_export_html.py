
import lxml
import html
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
            f.write(lxml.html.tostring(self.root, pretty_print=True).decode())

    def testsIterate(self, row):
        super().testsIterate(row)
        rdata = self.extract_info(row)
        trow = lxml.etree.SubElement(self.table, 'tr')
        try:
            for r in self.ROW_TEXTS:
                rh = lxml.etree.SubElement(trow, 'td')
                if r[self.KEY_INDEX] == self.KEY_DURATION:
                    rh.text = '{:.4f}'.format(rdata[r[self.KEY_INDEX]])
                else:
                    rh.text = rdata[r[self.KEY_INDEX]]

            if rdata[self.KEY_LOG] != '':
                h2 = lxml.etree.SubElement(self.logsection, 'h3')
                h2.text = rdata[self.KEY_TITLE]
                for l in rdata[self.KEY_LOG].splitlines():
                    p = lxml.etree.SubElement(self.logsection, 'p')
                    p.text = html.escape(l)
        except ValueError as e:
            print(f"Error reporting html: {e}")


    def create_base(self):
        repname = self.header[cst.DB_TEST_SET_NAME]
        if self.name != '':
            repname = self.name

        self.root = lxml.etree.Element('html', lang='en')
        head = lxml.etree.SubElement(self.root, 'head')
        title = lxml.etree.SubElement(head, 'title')
        title.text = repname
        self.body = lxml.etree.SubElement(self.root, 'body')
        h1 = lxml.etree.SubElement(self.body, 'h1')
        h1.text = repname

        div = lxml.etree.SubElement(self.body, 'div')
        h2 = lxml.etree.SubElement(div, 'h2')
        h2.text = 'Test conditions'

        for k in self.HEADER_TEXTS.keys():
            if k in self.header.keys():
                h = lxml.etree.SubElement(div, 'h3')
                h.text = self.HEADER_TEXTS[k]
                p = lxml.etree.SubElement(div, 'p')
                p.text = self.header[k]

        div = lxml.etree.SubElement(self.body, 'div')
        h2 = lxml.etree.SubElement(div, 'h2')
        h2.text = 'Test results'

        self.table = lxml.etree.SubElement(self.body, 'table')
        row = lxml.etree.SubElement(self.table, 'tr')
        for r in self.ROW_TEXTS:
            rh = lxml.etree.SubElement(row, 'th')
            rh.text = r[self.TEXT_INDEX]

        self.logsection = lxml.etree.SubElement(self.body, 'div')
        h2 = lxml.etree.SubElement(self.logsection, 'h2')
        h2.text = 'Logs'
