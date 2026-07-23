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
    | ``cmd``         | /                     | ``command`` export only: the external     |
    |                 |                       | command line to run (see below).          |
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

.. _sec_reports_command:

``command`` export — external tool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``command`` export post-processes the report with any external program.
The report database is copied to a temporary SQLite file and the command runs
on the host system (even from the Flatpak / AppImage sandboxes):

.. code-block:: yaml
    :caption: post-processing the report with an external tool

    report:
        export:
            - command:
                cmd: mytool --input {db} --output {out}
                path: $(home)/reports
                file_name: $(test_name).pdf

Two placeholders are substituted in ``cmd``:

* ``{db}``  — path of the temporary SQLite copy of the report
  (tables described below);
* ``{out}`` — the output path built from ``path`` / ``file_name``.

The command runs with the test directory as working directory, so relative
paths behave as elsewhere in the ``.tum`` file.

A command that cannot be started or exits with a non-zero code produces an
``[report] Export skipped: ...`` info line; the test run continues.

.. _sec_reports_plugins:

Custom export formats (plugins)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A third-party Python package can register additional export formats via the
``testium.exporters`` setuptools entry point group. The plugin must be
installed with the **host** Python interpreter (the one resolved as
``python_bin``, also used by ``py_func``) — a plain ``pip install`` there is
enough, no testium configuration change. The format can then be referenced
from the YAML by its declared name, in **every** install channel: source,
wheel, PyInstaller, Flatpak and AppImage. The plugin runs in a separate host
process on a temporary SQLite copy of the report.

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
