
import re
import lxml.html
import lxml.etree
from runtime.testium_report import Exporter
import interpreter.utils.constants as cst

_INVALID_XML_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]')


def _sanitize(s):
    """Silently strip the characters lxml cannot serialize (C0 except
    \t\n\r, DEL, C1), the same policy junit_xml already applies."""
    return _INVALID_XML_RE.sub('', s)

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
        try:
            trow = lxml.etree.SubElement(self.table, 'tr')
            for text in (row.name, row.message,
                         '{:.4f}'.format(row.duration_s), row.result):
                rh = lxml.etree.SubElement(trow, 'td')
                rh.text = _sanitize(text)

            log = row.log or ''
            if log != '':
                h2 = lxml.etree.SubElement(self.logsection, 'h3')
                h2.text = _sanitize(row.name)
                for l in log.splitlines():
                    p = lxml.etree.SubElement(self.logsection, 'p')
                    p.text = _sanitize(l)
        except ValueError as e:
            print(f'[report] HTML export: cannot render row for test '
                  f'"{row.name}": {e}')


    def create_base(self):
        repname = self.report.header[cst.DB_TEST_SET_NAME]
        if self.name != '':
            repname = self.name

        self.root = lxml.etree.Element('html', lang='en')
        head = lxml.etree.SubElement(self.root, 'head')
        title = lxml.etree.SubElement(head, 'title')
        title.text = _sanitize(repname)
        self.body = lxml.etree.SubElement(self.root, 'body')
        h1 = lxml.etree.SubElement(self.body, 'h1')
        h1.text = _sanitize(repname)

        div = lxml.etree.SubElement(self.body, 'div')
        h2 = lxml.etree.SubElement(div, 'h2')
        h2.text = 'Test conditions'

        for k in self.HEADER_TEXTS.keys():
            if k in self.report.header.keys():
                h = lxml.etree.SubElement(div, 'h3')
                h.text = self.HEADER_TEXTS[k]
                p = lxml.etree.SubElement(div, 'p')
                p.text = _sanitize(self.report.header[k])

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
