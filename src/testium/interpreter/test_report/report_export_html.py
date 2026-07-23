
import lxml.html
import lxml.etree
import html
from runtime.testium_report import Exporter
import interpreter.utils.constants as cst

class ReportExportHTML(Exporter):
    HEADER_TEXTS = {
        'test_file': 'Test file name',
        'test_name': 'Test name',
        'testrun_date': 'Date of the test',
        'testrun_time': 'Time of the test',
        'test_revision': 'Git revision of the test',
        'report_version': 'Report tool version',
    }
    COLUMN_TITLES = ['Test title', 'Message', 'Duration (s)', 'Test Result']

    def export(self):
        self.create_base()
        for row in self.rows:
            self.add_row(row)
        with open(self.out_path, 'w', encoding="utf-8") as f:
            f.write(lxml.html.tostring(self.root, pretty_print=True).decode())

    def add_row(self, row):
        trow = lxml.etree.SubElement(self.table, 'tr')
        try:
            for text in (row.name, row.message,
                         '{:.4f}'.format(row.duration_s), row.result):
                rh = lxml.etree.SubElement(trow, 'td')
                rh.text = text

            log = row.log or ''
            if log != '':
                h2 = lxml.etree.SubElement(self.logsection, 'h3')
                h2.text = row.name
                for l in log.splitlines():
                    p = lxml.etree.SubElement(self.logsection, 'p')
                    p.text = html.escape(l)
        except ValueError as e:
            print(f"Error reporting html: {e}")


    def create_base(self):
        repname = self.report.header[cst.DB_TEST_SET_NAME]
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
            if k in self.report.header.keys():
                h = lxml.etree.SubElement(div, 'h3')
                h.text = self.HEADER_TEXTS[k]
                p = lxml.etree.SubElement(div, 'p')
                p.text = self.report.header[k]

        div = lxml.etree.SubElement(self.body, 'div')
        h2 = lxml.etree.SubElement(div, 'h2')
        h2.text = 'Test results'

        self.table = lxml.etree.SubElement(self.body, 'table')
        row = lxml.etree.SubElement(self.table, 'tr')
        for title_text in self.COLUMN_TITLES:
            rh = lxml.etree.SubElement(row, 'th')
            rh.text = title_text

        self.logsection = lxml.etree.SubElement(self.body, 'div')
        h2 = lxml.etree.SubElement(self.logsection, 'h2')
        h2.text = 'Logs'
