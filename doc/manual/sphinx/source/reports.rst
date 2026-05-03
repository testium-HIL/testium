.. _sec_reports:

Reports
---------

If a report is required (in addition to the log), the ``report`` YAML element
must be added at the root of the TUM main test file.

The ``report`` element accepts a single export or a list of them under the
``export`` key. Each export entry uses the format name as its key:

.. code-block:: yaml
    :caption: reports global settings — multiple exports

    report:
        enabled: True
        log_stored: True
        export:
            - sqlite:
                path: $(home)/reports
                file_name: $(test_name).db
            - junit:
                path: $(home)/reports
                file_name: $(test_name).xml
            - html:
                path: $(home)/reports
                file_name: $(test_name).html

.. table:: report attributes
    :widths: 20, 30, 50

    +-----------------+-----------------------+-------------------------------------------+
    | Attribute       | default value         | Description                               |
    +-----------------+-----------------------+-------------------------------------------+
    | ``enabled``     | ``True``              | Report activated                          |
    +-----------------+-----------------------+-------------------------------------------+
    | ``log_stored``  | ``False``             | When ``True``, captures stdout per test   |
    |                 |                       | item so exports (html, json) can include  |
    |                 |                       | the log of each item.                     |
    +-----------------+-----------------------+-------------------------------------------+
    | ``export``      | /                     | One export entry or a list of them. Each  |
    |                 |                       | entry's key is the format name (see       |
    |                 |                       | below).                                   |
    +-----------------+-----------------------+-------------------------------------------+

Each export entry supports the following sub-attributes:

.. table:: export attributes
    :widths: 20, 30, 50

    +-----------------+-----------------------+-------------------------------------------+
    | Attribute       | default value         | Description                               |
    +-----------------+-----------------------+-------------------------------------------+
    | ``path``        | ``$(report_path)``    | Output directory.                         |
    +-----------------+-----------------------+-------------------------------------------+
    | ``file_name``   | /                     | Output file name. May include             |
    |                 |                       | ``$(...)`` global-dict expansions.        |
    +-----------------+-----------------------+-------------------------------------------+
    | ``pattern``     | /                     | One or more SQL ``LIKE`` patterns         |
    |                 |                       | applied on the test ``name``.             |
    +-----------------+-----------------------+-------------------------------------------+
    | ``key``         | /                     | One or more SQL ``LIKE`` patterns         |
    |                 |                       | applied on the test ``key``               |
    |                 |                       | (the per-item ``key`` attribute).         |
    +-----------------+-----------------------+-------------------------------------------+

Built-in formats
^^^^^^^^^^^^^^^^

* ``sqlite`` — raw SQLite database (storage layer; selecting it persists the run).
* ``text``   — simple indented text dump of the test tree.
* ``json``   — full report as JSON: ``{"header": {...}, "tests": [...]}``.
* ``junit``  — JUnit XML (requires the ``junit_xml`` Python package).
* ``html``   — single HTML page with header, results table and per-item logs (requires ``lxml``).

If a format is unknown or its optional dependency is missing, the export is
skipped with an ``[report] Export skipped: ...`` info line on stdout — the
test run is **not** interrupted.

.. _sec_reports_plugins:

Custom export formats (plugins)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A third-party Python package can register additional export formats via the
``testium.exporters`` setuptools entry point group. Once installed in the same
Python environment as testium, the format is auto-detected at startup and can
be referenced from the YAML by its declared name.

Plugin contract — a class with this constructor signature:

.. code-block:: python
    :caption: minimal exporter contract

    class MyExporter:
        def __init__(self, name, con, path, pats, keys, no_header=False):
            # name      : str  — report name
            # con       : sqlite3.Connection (read) — tables: header, tests
            # path      : str  — output file path (already expansed)
            # pats      : list[str] — LIKE filters on test_name (may be empty)
            # keys      : list[str] — LIKE filters on report_key (may be empty)
            # no_header : bool — skip header section (set by the inline
            #             `report` test item)
            ...  # do the work in __init__ and write to `path`

Tables and columns of the SQLite report:

* ``header(key TEXT, value TEXT)`` — keys: ``report_version``, ``test_file``,
  ``test_name``, ``test_result``, ``test_revision``, ``testium_version``,
  ``testrun_date``, ``testrun_time``, ``test_duration``.
* ``tests`` — 12 columns: ``timestamp_start``, ``test_id``, ``parent_id``,
  ``level``, ``test_name``, ``test_type``, ``report_key``, ``result``
  (``PASS``/``FAIL``/``SKIP``), ``message``, ``duration`` (ms),
  ``log`` (captured stdout when ``log_stored: True``), ``data`` (JSON of
  values reported via ``self.reportValue(...)``).

Declaration in the plugin's ``pyproject.toml``:

.. code-block:: toml
    :caption: registering an exporter via entry-points

    [project.entry-points."testium.exporters"]
    my_format = "my_pkg:MyExporter"

The plugin is then usable in any ``.tum`` report block as ``my_format:`` —
no testium configuration change required.
