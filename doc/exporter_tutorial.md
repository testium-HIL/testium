# Tutorial — writing a report exporter

This walk-through creates a custom report export format, `csv_summary`,
and uses it from a `.tum` file like any built-in format (`text`, `json`,
`junit`, `html`). An exporter is a small pip package installed beside
testium — it works with every install channel (source, wheel,
PyInstaller, Flatpak, AppImage).

For one-shot needs, the `command` export (see the manual, Reports
chapter) can call any external tool without writing a package; an
exporter plugin is the right tool for a reusable, named format.

## How exporters run

At the end of a run (or at an inline `report` test item), testium copies
the report database to a temporary SQLite file and calls your exporter
class **on the host Python** — the interpreter resolved as `python_bin`,
the same one running your `py_func` steps. Any error skips the export
with an `[report] Export skipped: ...` log line; the test run never
breaks.

You do not need SQL: testium ships a helper module, `testium_report`,
importable by your plugin with no installation step (the process that
loads your class resolves it from the running testium — same version,
every channel). The built-in formats are written on the same helper.

## Step 1 — the package

Two files:

```
csv-summary/
├── pyproject.toml
└── csv_summary.py
```

`csv_summary.py` — subclass `Exporter` and implement `export()`:

```python
"""testium report exporter producing a one-line-per-test CSV summary."""
import csv

from testium_report import Exporter


class CsvSummary(Exporter):
    def export(self):
        with open(self.out_path, "w", newline="", encoding="utf-8") as f:
            out = csv.writer(f)
            if not self.no_header:
                for key, value in self.report.header.items():
                    out.writerow(["#", key, value])
            out.writerow(["test_name", "test_type", "result",
                          "duration_s", "message"])
            for row in self.rows:
                out.writerow([row.name, row.type, row.result,
                              "{:.3f}".format(row.duration_s), row.message])
```

The base class hands you everything prepared:

* `self.rows` — the test items, `pattern`/`key` filters of the export
  entry already applied. Each row has `name`, `type`, `key`, `result`
  (`PASS`/`FAIL`/`SKIP` — or the `passed`/`failed`/`skipped` booleans),
  `message`, `duration_s`, `level`, `log`, `data` (values reported by the
  item, JSON-decoded), `timestamp_start`.
* `self.report` — the whole report: `report.header` (dict: `test_file`,
  `test_name`, `test_result`, `testrun_date`, …), `report.rows(...)` for
  other filters, `report.tree()` for the item hierarchy (rows linked
  through `children`).
* `self.out_path` — the output file path; a pre-existing file has been
  renamed away (`-N.saved`), never overwritten.
* `self.name`, `self.no_header` — the report name, and whether the call
  comes from an inline `report` test item (mid-run partial report).

`pyproject.toml` — the entry-point line binds the format name (the key
you will write in the `.tum`) to the class:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "testium-csv-summary"
version = "0.1.0"
description = "CSV summary exporter for testium reports"

[project.entry-points."testium.exporters"]
csv_summary = "csv_summary:CsvSummary"

[tool.setuptools]
py-modules = ["csv_summary"]
```

## Step 2 — install

Install with the host Python (`python_bin`). No testium configuration
change is needed:

```sh
pip install ./csv-summary       # or: pip install -e ./csv-summary
```

The Flatpak / AppImage / Windows channels change nothing here: this is a
plain terminal command on the machine — the plugin lives beside testium,
never inside it. If `python_bin` points to a venv, install into that venv.

## Step 3 — use it

Reference the format by its entry-point name, in the top-level `report`
block:

```yaml
report:
    export:
        - csv_summary:
            path: $(home)/reports
            file_name: $(test_name).csv
```

or in an inline `report` test item (mid-run snapshot, `no_header` is set):

```yaml
        - report:
            name: partial summary
            export:
                - csv_summary:
                    path: $(home)/reports
                    file_name: partial.csv
                    pattern: "step%"
```

Run the test; the file appears next to the other exports:

```
#,test_file,/home/user/tests/mytest.tum
#,testrun_date,2026-07-23
...
test_name,test_type,result,duration_s,message
first step,Sleep,PASS,0.102,Sleep 0.01 sec
```

## Developing and testing the plugin

In your development environment (IDE resolution, unit tests without
testium running), install testium itself: the wheel exposes the same
helper as a regular top-level module.

```sh
pip install testium-<version>-py3-none-any.whl
python -c "from testium_report import Exporter"     # resolves
```

At execution the copy shipped inside the *running* testium always wins
over the pip-installed one, so the helper version can never diverge from
the testium producing the report. Without installing testium, pointing
`PYTHONPATH` at `<testium>/runtime` gives the same import.

You can unit-test an exporter against any saved report: `Report` also
accepts a file path.

```python
from testium_report import Report
rep = Report("validation-source.sqlite")
failed = [r.name for r in rep.rows() if r.failed]
```

## The raw contract (no helper)

`Exporter` only wraps the plugin contract; a class with this constructor
works without the helper, reading the SQLite tables itself (schema in the
manual, Reports chapter):

```python
class MyExporter:
    def __init__(self, name, con, path, pats, keys, no_header=False):
        ...  # con: sqlite3.Connection — tables: header, tests
```

## Troubleshooting

* `[report] Export skipped: format "csv_summary" not found. Available:
  ...` — the package is not visible from `python_bin`. Check with
  `<python_bin> -m pip show testium-csv-summary`. The `Available:` list
  shows every format actually found (built-ins + installed plugins).
* An exception in the class is reported as an `[report] Export skipped:`
  line with the message; the run continues.
* Extra pip dependencies of your exporter must be installed with the
  same host Python.

## Where to go next

* `test/validation/fake_exporter/` — the exporter used by the testium
  validation suite, same shape as this tutorial.
* Manual, Reports chapter — export attributes (`pattern`, `key`, paths),
  the `command` export and the report database description.
