.. _sec_reports:

Reports
---------

During a test run, testium records one row per executed test item — name,
type, result, message, duration, reported values — into a SQLite database,
together with a header describing the run (test file, date, global result,
…). A report **export** turns that database into an output file: JUnit XML,
HTML, JSON, plain text, the raw database itself, or any custom format.

This chapter describes:

* how to enable the report and declare exports
  (:ref:`declaring exports<sec_reports_declaring>`),
* the attributes accepted by every export entry
  (:ref:`export attributes<sec_reports_attributes>`),
* the built-in formats and the special role of ``sqlite``
  (:ref:`built-in formats<sec_reports_builtin>`),
* post-processing with an external program
  (:ref:`command export<sec_reports_command>`),
* adding custom formats as pip plugins
  (:ref:`exporter plugins<sec_reports_plugins>`),
* the report database schema
  (:ref:`database schema<sec_reports_schema>`).

.. _sec_reports_declaring:

Declaring exports
^^^^^^^^^^^^^^^^^

The ``report`` element at the root of the main ``.tum`` file enables the
recording and lists the exports. The ``export`` key takes one entry or a
list of entries; each entry uses the format name as its key:

.. code-block:: yaml
    :caption: report declaration — multiple exports

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
    | ``enabled``     | ``True``              | Enables report recording.                 |
    +-----------------+-----------------------+-------------------------------------------+
    | ``log_stored``  | ``False``             | When ``True``, the stdout of each test    |
    |                 |                       | item is captured during the run, so that  |
    |                 |                       | exports (``html``, ``json``) can include  |
    |                 |                       | the log of each item.                     |
    +-----------------+-----------------------+-------------------------------------------+
    | ``export``      | /                     | One export entry or a list of them. Each  |
    |                 |                       | entry's key is the format name (see       |
    |                 |                       | :ref:`sec_reports_builtin`,               |
    |                 |                       | :ref:`sec_reports_command`,               |
    |                 |                       | :ref:`sec_reports_plugins`).              |
    +-----------------+-----------------------+-------------------------------------------+

When the exports run:

* **at the end of the run** — each entry of the ``export`` list above
  produces one output file, in declaration order. This is the normal case.
* **during the run** — the :ref:`report test item<sec_report_test_item>`
  placed in the test sequence runs its own ``export`` list against the data
  collected so far. Useful to snapshot partial results in a long campaign.
* ``sqlite`` is the exception: it is not converted at the end but written
  live during the run (see :ref:`sec_reports_builtin`).

In :ref:`batch mode<sec_batch_mode>`, the ``-p``, ``-t`` and ``-n``
command-line options (see :ref:`-p<sec_p_param>`) **replace** the ``export``
list of the test file with a single export built from the given path, type
and patterns.

.. _sec_reports_attributes:

Export attributes
^^^^^^^^^^^^^^^^^

Every export entry accepts the following sub-attributes:

.. table:: export attributes
    :widths: 20, 30, 50

    +-----------------+-----------------------+-------------------------------------------+
    | Attribute       | default value         | Description                               |
    +-----------------+-----------------------+-------------------------------------------+
    | ``path``        | ``$(report_path)``    | Output directory.                         |
    +-----------------+-----------------------+-------------------------------------------+
    | ``file_name``   | /                     | Output file name.                         |
    +-----------------+-----------------------+-------------------------------------------+
    | ``pattern``     | /                     | One or more SQL ``LIKE`` patterns         |
    |                 |                       | applied on the test item ``name``.        |
    +-----------------+-----------------------+-------------------------------------------+
    | ``key``         | /                     | One or more SQL ``LIKE`` patterns         |
    |                 |                       | applied on the test item ``key``          |
    |                 |                       | attribute.                                |
    +-----------------+-----------------------+-------------------------------------------+
    | ``cmd``         | /                     | ``command`` export only: the external     |
    |                 |                       | command line to run                       |
    |                 |                       | (see :ref:`sec_reports_command`).         |
    +-----------------+-----------------------+-------------------------------------------+

``path`` and ``file_name`` are joined to build the output file; you can
also put the full path in just one of the two attributes. All attributes accept ``$(...)``
:ref:`global variable expansions<sec_variable_expansion>`, resolved at
export time — ``file_name: $(test_name).xml`` produces one report file per
test file, for example. If the output file already exists, it is renamed to
``<name>-<N>.saved`` first, never overwritten.

``pattern`` and ``key`` select which test items appear in the output.
Without them, every executed item is exported. Both use the SQL ``LIKE``
syntax — ``%`` matches any text, ``_`` one character — and accept a single
string or a list; an item is kept when it matches **any** of the given
patterns.

* ``pattern`` matches on the item ``name``;
* ``key`` matches on the item ``key`` attribute, one of the
  :ref:`common test item attributes<sec_item_common>`. The usual scheme is
  to tag related items with the same ``key`` in the ``.tum`` and filter the
  report on it:

.. code-block:: yaml
    :caption: selecting items with ``key``

    steps:
        - console:
            name: power on
            key: setup
            ...

    report:
        export:
            - junit:
                file_name: setup_only.xml
                key: setup

.. _sec_reports_builtin:

Built-in formats
^^^^^^^^^^^^^^^^

* ``sqlite`` — the report database itself (see below).
* ``text``   — indented text dump of the test tree.
* ``json``   — full report as JSON: ``{"header": {...}, "tests": [...]}``.
* ``junit``  — JUnit XML, for CI systems (requires the ``junit_xml``
  Python package).
* ``html``   — single HTML page with header, results table and per-item
  logs (requires ``lxml``).

``sqlite`` has a special role: it is not a conversion but the storage
layer itself. With a ``sqlite`` entry, the internal database is written
**live** to the given file during the run; the file remains afterwards for
any external analysis (schema in :ref:`sec_reports_schema`). Without it,
the database only lives in memory and disappears once the other exports
have run. Declaring several ``sqlite`` entries is pointless — only the
last ``path`` is used.

The ``html`` and ``json`` exports can embed the captured stdout of each
test item; this requires ``log_stored: True`` in the ``report`` block (see
:ref:`sec_reports_declaring`).

If a format is unknown, or an optional dependency is missing, the export
is skipped with an ``[report] Export skipped: ...`` line on stdout and the
test run **continues**. The line lists the available formats: built-ins,
``command``, plus every installed plugin.

.. _sec_reports_command:

``command`` export — external tool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``command`` export post-processes the report with any external
program. The report database is copied to a temporary SQLite file and the
command runs on the host system (even from the Flatpak / AppImage
sandboxes):

.. code-block:: yaml
    :caption: post-processing the report with an external tool

    report:
        export:
            - command:
                cmd: mytool --input $(db) --output $(out)
                path: $(home)/reports
                file_name: $(test_name).pdf

Two placeholders, following the usual ``$(...)`` syntax, are reserved in
``cmd`` (they are resolved by the export itself, not from the global
variables):

* ``$(db)``  — path of the temporary SQLite copy of the report
  (schema in :ref:`sec_reports_schema`);
* ``$(out)`` — the output path built from ``path`` / ``file_name``.

``cmd`` is split shell-style (quotes group words) but **not** run through
a shell: no pipes, redirections or globbing — wrap them in a script if
needed. Other ``$(...)`` :ref:`expansions<sec_variable_expansion>` work as
usual, so ``$(python_bin) myscript.py $(db) $(out)`` runs a script with
the same interpreter as :ref:`py_func<sec_py_func_item>`. The command runs
with the test directory as working directory, so relative paths behave as
elsewhere in the ``.tum`` file. The temporary ``$(db)`` copy is deleted
after the command returns — the command must not rely on it afterwards.

The command output (stdout) is forwarded to the test log. A command that
cannot be started or exits with a non-zero code produces an
``[report] Export skipped: ...`` line (with its stderr); the test run
continues.

.. _sec_reports_plugins:

Custom export formats (plugins)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A third-party Python package can register additional export formats via
the ``testium.exporters`` setuptools entry point group. A step-by-step
tutorial (package layout, install, use) is provided in
``doc/exporter_tutorial.md`` of the source repository; this section is the
reference.

The plugin must be installed with the **host** Python interpreter — the
one resolved as ``python_bin`` and used by
:ref:`py_func<sec_py_func_item>`. A plain ``pip install`` with that
interpreter is enough; no testium configuration change is needed. The
format is then usable in any ``.tum``
by its declared name, in **every** install channel: source, wheel,
PyInstaller, Flatpak and AppImage.

Execution model: any format name that is not a built-in is looked up on
the host. testium copies the report database to a temporary SQLite file,
spawns the host Python, scans the installed ``testium.exporters`` entry
points there, loads the matching class and instantiates it with the
database copy. Consequences:

* the plugin (and any dependency it imports) must be installed with
  ``python_bin``'s ``pip`` — not inside the testium bundle, which is
  read-only in the frozen channels;
* the plugin cannot use testium internals — it only sees the SQLite
  database (:ref:`sec_reports_schema`) and its constructor arguments;
* a crash in the plugin (or a missing plugin dependency) skips that
  export with an ``[report] Export skipped: ...`` line and the run
  continues.

The plugin declares its format name in its ``pyproject.toml``:

.. code-block:: toml
    :caption: registering an exporter via entry-points

    [project.entry-points."testium.exporters"]
    my_format = "my_pkg:MyExporter"

The ``testium_report`` helper
"""""""""""""""""""""""""""""

The recommended way to write an exporter is the ``testium_report`` helper
module shipped with testium (the built-in formats are implemented with
it). It
is importable by the plugin with **no installation step**: the process
loading the plugin class resolves it from the running testium, so its
version always matches. Subclass ``Exporter`` and implement ``export()``:

.. code-block:: python
    :caption: exporter built on the helper

    from testium_report import Exporter

    class MyExporter(Exporter):
        def export(self):
            # self.rows      : filtered items — .name .type .key .result
            #                  (.passed/.failed/.skipped), .message,
            #                  .duration_s, .level, .log, .data (decoded)
            # self.report    : .header dict, .rows(pats, keys), .tree()
            # self.out_path  : output path (previous file renamed .saved)
            # self.name / self.no_header : report name, inline-item call
            with open(self.out_path, "w") as f:
                for row in self.rows:
                    f.write(f"{row.name}: {row.result}\n")

``Report`` also accepts a database file path instead of a connection,
which makes exporters easy to unit-test against a saved ``sqlite``
report. For the development environment (IDE, tests),
``pip install testium`` provides the same ``testium_report`` module as a
regular top-level import; at execution under testium the shipped copy
takes precedence.

Writing an exporter without the helper
""""""""""""""""""""""""""""""""""""""

The helper is optional. To run an export, testium only instantiates the
plugin class with the arguments below — a class with this constructor can
read the SQLite tables (:ref:`sec_reports_schema`) directly, without
``testium_report``:

.. code-block:: python
    :caption: minimal exporter class

    class MyExporter:
        def __init__(self, name, con, path, pats, keys, no_header=False):
            # name      : str  — report name
            # con       : sqlite3.Connection (read) — tables: header, tests
            # path      : str  — output file path (variables already expanded)
            # pats      : list[str] — LIKE filters on test_name (may be empty)
            # keys      : list[str] — LIKE filters on report_key (may be empty)
            # no_header : bool — do not write the run header (set when the
            #             export comes from an inline `report` test item)
            ...  # do the work in __init__ and write to `path`

.. _sec_reports_schema:

Report database schema
^^^^^^^^^^^^^^^^^^^^^^

The SQLite database produced by the ``sqlite`` export — and passed to
``command`` exports and plugins as a temporary copy — holds two tables.

``header`` — one ``(key TEXT, value TEXT)`` row per run property:
``report_version``, ``test_file``, ``test_name``, ``test_result``,
``test_revision``, ``testium_version``, ``testrun_date``,
``testrun_time``, ``test_duration``.

``tests`` — one row per executed test item, 12 columns:

.. table:: ``tests`` table columns
    :widths: 25, 75

    +---------------------+---------------------------------------------------+
    | Column              | Content                                           |
    +---------------------+---------------------------------------------------+
    | ``timestamp_start`` | Start timestamp; the table is ordered on it.      |
    +---------------------+---------------------------------------------------+
    | ``test_id``         | Unique item id.                                   |
    +---------------------+---------------------------------------------------+
    | ``parent_id``       | ``test_id`` of the enclosing item (tree           |
    |                     | structure).                                       |
    +---------------------+---------------------------------------------------+
    | ``level``           | Nesting depth.                                    |
    +---------------------+---------------------------------------------------+
    | ``test_name``       | Item ``name`` attribute.                          |
    +---------------------+---------------------------------------------------+
    | ``test_type``       | Item type (``Console``, ``Sleep``, …).            |
    +---------------------+---------------------------------------------------+
    | ``report_key``      | Item ``key`` attribute                            |
    |                     | (see :ref:`sec_item_common`).                     |
    +---------------------+---------------------------------------------------+
    | ``result``          | ``PASS``, ``FAIL`` or ``SKIP``.                   |
    +---------------------+---------------------------------------------------+
    | ``message``         | Result message.                                   |
    +---------------------+---------------------------------------------------+
    | ``duration``        | Item duration (0.1 ms units).                     |
    +---------------------+---------------------------------------------------+
    | ``log``             | Captured stdout of the item, when                 |
    |                     | ``log_stored: True``.                             |
    +---------------------+---------------------------------------------------+
    | ``data``            | JSON of the values reported by the item — e.g.    |
    |                     | ``reportValue(...)`` in a                         |
    |                     | :ref:`py_func<sec_py_func_item>`.                 |
    +---------------------+---------------------------------------------------+
