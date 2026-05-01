"""CSV report exporter — used as a real plugin by the testium validation suite.

Demonstrates the contract: take the SQLite connection, output path, optional
name/key filters, and produce the output. Has no dependency on testium
internals.
"""

import csv


class FakeExporter:
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

    def __init__(self, name, con, path, pats, keys, no_header=False):
        clauses = []
        for p in pats:
            clauses.append(f'test_name LIKE "{p}"')
        for k in keys:
            clauses.append(f'report_key LIKE "{k}"')
        where = ('WHERE ' + ' OR '.join(clauses) + ' ') if clauses else ''
        cols = ', '.join(self.COLUMNS)
        rows = con.execute(
            f'SELECT {cols} FROM tests {where}ORDER BY timestamp_start'
        ).fetchall()

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not no_header:
                writer.writerow(self.COLUMNS)
            for row in rows:
                writer.writerow(row)
