"""Report access helper for testium exporters.

Public API for reading a testium report database without SQL: ``Report``
(header + filtered test rows + tree), ``TestRow`` (typed row) and
``Exporter`` (base class implementing the exporter plugin contract).

Import names, all pointing to this file:
- ``testium_report``          — in the export worker process, where plugins
  run (the worker's directory is on sys.path); also from an installed
  testium wheel (top-level shim module).
- ``runtime.testium_report``  — in-process, used by the built-in exporters.

Must stay stdlib-only: the worker process has no testium installed.
"""
import json
import os
import sqlite3

# tests table columns, in schema order (report schema v0.1).
_COLUMNS = ["timestamp_start", "test_id", "parent_id", "level", "test_name",
            "test_type", "report_key", "result", "message", "duration",
            "log", "data"]

# TestRow.to_dict() key order — kept identical to the historical JSON export.
_DICT_FIELDS = ["timestamp_start", "test_id", "parent_id", "test_name",
                "test_type", "report_key", "result", "message", "duration",
                "data", "level", "log"]

# Attribute name -> column name where they differ.
_ATTR_TO_COLUMN = {"id": "test_id", "name": "test_name",
                   "type": "test_type", "key": "report_key"}


def prepare_file_to_save(file_name, file_ext=""):
    """Return the output path, renaming any pre-existing file to
    ``<name>-N.saved`` first (never overwrites a previous report)."""
    iname = file_name
    if file_ext != "":
        iname = os.path.splitext(file_name)[0] + file_ext

    if os.path.isfile(iname):
        i = 0
        fname = iname
        while os.path.isfile(fname):
            i += 1
            fname = iname + "-" + str(i) + ".saved"
        os.rename(iname, fname)
    return iname


class TestRow:
    """One executed test item.

    Attributes: ``timestamp_start``, ``id``, ``parent_id``, ``level``,
    ``name``, ``type``, ``key``, ``result`` ('PASS'/'FAIL'/'SKIP'),
    ``message``, ``duration`` (raw DB value), ``log``, ``children``
    (filled by Report.tree()).
    """

    def __init__(self, values):
        (self.timestamp_start, self.id, self.parent_id, self.level,
         self.name, self.type, self.key, self.result, self.message,
         self.duration, self.log, self._raw_data) = values
        self.children = []

    @property
    def passed(self):
        return self.result == "PASS"

    @property
    def failed(self):
        return self.result == "FAIL"

    @property
    def skipped(self):
        return self.result == "SKIP"

    @property
    def duration_s(self):
        """Duration in seconds (the DB stores 0.1 ms ticks)."""
        return (self.duration or 0) / 10000.0

    @property
    def data(self):
        """Values reported by the item (``store_result``, ``reportValue``):
        decoded from JSON when possible, else the raw string."""
        raw = self._raw_data
        if isinstance(raw, bytes):
            raw = raw.decode()
        if isinstance(raw, str) and raw.strip():
            try:
                return json.loads(raw)
            except ValueError:
                pass
        return raw

    def to_dict(self):
        """Plain dict with the DB field names — same keys, order and data
        decoding rule as the built-in JSON export."""
        ret = {}
        for field in _DICT_FIELDS:
            attr = field
            for a, col in _ATTR_TO_COLUMN.items():
                if col == field:
                    attr = a
            value = self._raw_data if field == "data" else getattr(self, attr)
            if isinstance(value, bytes):
                value = value.decode()
            # Historical rule: only JSON objects are decoded in the dict.
            if field == "data" and isinstance(value, str) \
                    and value.strip().startswith("{"):
                value = json.loads(value)
            ret[field] = value
        return ret


class Report:
    """Read access to a testium report database.

    ``db`` is either an open ``sqlite3.Connection`` or a file path.
    ``header`` is the header table as a plain dict (``test_file``,
    ``test_name``, ``testrun_date``, ``test_result``, ...).
    """

    def __init__(self, db):
        self._own_con = isinstance(db, str)
        self.con = sqlite3.connect(db) if self._own_con else db
        self.header = {}
        for key, value in self.con.execute("SELECT key, value FROM header"):
            self.header[key] = value

    def close(self):
        """Close the connection — only if it was opened from a path."""
        if self._own_con:
            self.con.close()

    def rows(self, pats=(), keys=()):
        """Flat list of TestRow ordered by start time.

        ``pats`` / ``keys`` are SQL LIKE filters (string or list) on the
        item name / key; a row is kept when it matches any of them.
        """
        pats = [pats] if isinstance(pats, str) else list(pats)
        keys = [keys] if isinstance(keys, str) else list(keys)
        where, params = [], []
        for p in pats:
            where.append("test_name LIKE ?")
            params.append(p)
        for k in keys:
            where.append("report_key LIKE ?")
            params.append(k)
        sql = "SELECT " + ", ".join(_COLUMNS) + " FROM tests"
        if where:
            sql += " WHERE " + " OR ".join(where)
        sql += " ORDER BY timestamp_start"
        return [TestRow(v) for v in self.con.execute(sql, params)]

    def tree(self, pats=(), keys=()):
        """Same rows linked as a hierarchy via parent_id: returns the root
        rows, each with its ``children`` filled (recursively). A row whose
        parent is filtered out becomes a root."""
        rows = self.rows(pats, keys)
        by_id = {r.id: r for r in rows}
        roots = []
        for r in rows:
            parent = by_id.get(r.parent_id)
            if parent is not None and parent is not r:
                parent.children.append(r)
            else:
                roots.append(r)
        return roots


class Exporter:
    """Base class implementing the exporter plugin contract.

    Subclass and override ``export()``; available attributes:
    ``self.report`` (Report), ``self.rows`` (filtered TestRow list),
    ``self.out_path`` (output file path, previous file rotated away),
    ``self.name``, ``self.pats``, ``self.keys``, ``self.no_header``.
    """

    def __init__(self, name, con, path, pats, keys, no_header=False):
        self.name = name
        self.pats = [pats] if isinstance(pats, str) else list(pats)
        self.keys = [keys] if isinstance(keys, str) else list(keys)
        self.no_header = no_header
        self.report = Report(con)
        self.rows = self.report.rows(self.pats, self.keys)
        self.out_path = prepare_file_to_save(path)
        try:
            self.export()
        finally:
            self.report.close()

    def export(self):
        raise NotImplementedError
