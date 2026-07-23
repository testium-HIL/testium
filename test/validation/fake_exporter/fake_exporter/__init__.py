"""CSV report exporter — used as a real plugin by the testium validation suite.

Built on the ``testium_report`` helper shipped with testium: it is importable
here because the plugin class is loaded by the export worker, whose directory
(testium's ``runtime/``) is on sys.path. Exercises Exporter/Report/TestRow
end to end.
"""

import csv

from testium_report import Exporter


class FakeExporter(Exporter):
    COLUMNS = [
        'timestamp_start',
        'test_id',
        'parent_id',
        'level',
        'test_name',
        'test_type',
        'report_key',
        'result',
        'message',
        'duration',
    ]

    def export(self):
        with open(self.out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not self.no_header:
                writer.writerow(self.COLUMNS)
            for row in self.rows:
                writer.writerow([row.timestamp_start, row.id, row.parent_id,
                                 row.level, row.name, row.type, row.key,
                                 row.result, row.message, row.duration])
