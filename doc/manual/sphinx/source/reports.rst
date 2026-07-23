.. _sec_reports:

Reports
---------

If a report is required (in addition to the log), the ``report`` YAML element
must be added at the root of the TUM main test file.

During the run, testium records one row per executed test item (name, type,
result, message, duration, …) into an internal SQLite database. The
``export`` entries decide what becomes of that database **at the end of the
run**: each entry produces one output file, in declaration order. Exports can
also be produced *during* the run with the ``report`` test item (see the test
items chapter): it runs its own ``export`` list against the data collected so
far, which is useful to snapshot partial results in a long campaign.

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

Details:

* ``path`` and ``file_name`` are joined to build the output file; giving the
  full path in either one alone also works. All values accept ``$(...)``
  expansions, resolved at export time — ``$(test_name)`` produces one report
  file per test file, for example.
* ``pattern`` and ``key`` restrict which test items appear in the output.
  They use the SQL ``LIKE`` syntax (``%`` matches anything, ``_`` one
  character) and can be a single string or a list; an item is kept when it
  matches **any** of the given patterns. ``pattern`` matches on the item
  ``name``, ``key`` on the item ``key`` attribute — the usual scheme is to
  tag items with ``key`` in the ``.tum`` and filter the report on it.
  Without ``pattern``/``key`` every executed item is exported.

Built-in formats
^^^^^^^^^^^^^^^^

* ``sqlite`` — raw SQLite database (storage layer; selecting it persists the run).
* ``text``   — simple indented text dump of the test tree.
* ``json``   — full report as JSON: ``{"header": {...}, "tests": [...]}``.
* ``junit``  — JUnit XML (requires the ``junit_xml`` Python package).
* ``html``   — single HTML page with header, results table and per-item logs (requires ``lxml``).

``sqlite`` has a special role: it is not a conversion but the storage layer
itself. With a ``sqlite`` entry, the internal database is written **live** to
the given file during the run (usable afterwards for any external analysis,
with the schema described at the end of this chapter). Without it the
database only lives in memory and disappears after the other exports ran.
Declaring several ``sqlite`` entries is pointless — the last ``path`` wins.

The ``html`` and ``json`` exports can embed the captured stdout of each test
item; this requires ``log_stored: True`` in the ``report`` block, which
enables the per-item capture during the run.

If a format is unknown or its optional dependency is missing, the export is
skipped with an ``[report] Export skipped: ...`` info line on stdout — the
test run is **not** interrupted. The line lists the available formats:
built-ins, ``command``, plus every installed plugin (see below).

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

``cmd`` is split shell-style (quotes group words) but **not** run through a
shell: no pipes, redirections or globbing — wrap them in a script if needed.
It accepts ``$(...)`` expansions, so ``$(python_bin) myscript.py {db} {out}``
runs a script with the same interpreter as ``py_func``. The command runs
with the test directory as working directory, so relative paths behave as
elsewhere in the ``.tum`` file. The temporary ``{db}`` copy is deleted after
the command returns — the command must not rely on it afterwards.

The command output (stdout) is forwarded to the test log. A command that
cannot be started or exits with a non-zero code produces an
``[report] Export skipped: ...`` info line (with its stderr); the test run
continues.

.. _sec_reports_plugins:

Custom export formats (plugins)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A third-party Python package can register additional export formats via the
``testium.exporters`` setuptools entry point group. The plugin must be
installed with the **host** Python interpreter (the one resolved as
``python_bin``, also used by ``py_func``) — a plain ``pip install`` there is
enough, no testium configuration change. The format can then be referenced
from the YAML by its declared name, in **every** install channel: source,
wheel, PyInstaller, Flatpak and AppImage.

Execution model: any format name that is not a built-in is looked up on the
host. testium copies the report database to a temporary SQLite file, spawns
the host Python, scans the installed ``testium.exporters`` entry points
there, loads the matching class and calls it with its own connection on the
copy. Consequences:

* the plugin (and any dependency it imports) must be installed with
  ``python_bin``'s ``pip`` — not inside the testium bundle, which is
  read-only in the frozen channels;
* the plugin cannot use testium internals — it only sees the SQLite
  database and its constructor arguments;
* a crash in the plugin (or a missing plugin dependency) skips that export
  with an ``[report] Export skipped: ...`` line and the run continues.

A step-by-step walk-through (package layout, install, use) is provided in
``doc/exporter_tutorial.md`` of the source repository.

The ``testium_report`` helper
"""""""""""""""""""""""""""""

The recommended way to write an exporter is the ``testium_report`` helper
module shipped with testium (the built-in formats are written on it). It is
importable by the plugin with **no installation step**: the process loading
the plugin class resolves it from the running testium, so its version always
matches. Subclass ``Exporter`` and implement ``export()``:

.. code-block:: python
    :caption: exporter built on the helper

    from testium_report import Exporter

    class MyExporter(Exporter):
        def export(self):
            # self.rows      : filtered items — .name .type .key .result
            #                  (.passed/.failed/.skipped), .message,
            #                  .duration_s, .level, .log, .data (decoded)
            # self.report    : .header dict, .rows(pats, keys), .tree()
            # self.out_path  : output path (previous file rotated away)
            # self.name / self.no_header : report name, inline-item call
            with open(self.out_path, "w") as f:
                for row in self.rows:
                    f.write(f"{row.name}: {row.result}\n")

``Report`` also accepts a database file path instead of a connection, which
makes exporters easy to unit-test against a saved ``sqlite`` report. For the
development environment (IDE, tests), ``pip install testium`` provides the
same ``testium_report`` module as a regular top-level import; at execution
under testium the shipped copy takes precedence.

Raw contract
""""""""""""

The helper base class only wraps the actual plugin contract — a class with
this constructor signature, free to read the SQLite tables itself:

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
