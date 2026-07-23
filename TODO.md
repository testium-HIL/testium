# TODO — Report exporter rework

## Why

Third-party report exporters are discovered with
`importlib.metadata.entry_points(group="testium.exporters")` at import of
`src/testium/interpreter/test_report/test_report.py`, i.e. in the site-packages
of the **running** interpreter. In Flatpak, AppImage and PyInstaller builds that
interpreter is bundled and read-only: the user cannot `pip install` anything
into it, so plugins can never be seen. The mechanism only works for source and
wheel installs.

Decision: plugins are discovered and executed on the **host** Python
(`bins.python_bin()`, same philosophy as `py_func`/`pytest`), plus a new
`command` export type for arbitrary external tools. The in-process entry-points
scan is **removed** (replaced, not kept).

Built-in exporters (`text`, `json`, `junit`, `html`, `sqlite`) are untouched:
they run in-process on the live connection and their dependencies (`junit-xml`,
`lxml`) are hard requirements bundled in every channel (`src/requirements.txt`,
collected explicitly by the PyInstaller `.spec`). Moving them host-side would be
a regression (a built-in format would start requiring a host `pip install`).
Only non-builtin format names route to the host worker.

## A — Host-side pip plugin exporters

1. Remove `_discover_plugins()` from
   `src/testium/interpreter/test_report/test_report.py`.
2. New stdlib-only worker, e.g. `src/testium/runtime/export_worker.py`
   (in `runtime/` so it is staged for Flatpak by `_get_host_testium_path()`
   and respects the py_func isolation contract). It receives JSON params via
   argv (format, db path, output path, pats, keys, no_header, name), scans
   `entry_points(group="testium.exporters")` **on the host interpreter**,
   loads the class, opens its own `sqlite3` connection and runs the unchanged
   contract `cls(name, con, path, pats, keys, no_header)`.
   Unknown format → prints the available-formats list with a sentinel;
   any error → non-zero exit + stderr.
3. `Export.exec` (`test_report.py`): non-builtin format → materialize the DB
   to a temp file under `/tmp` (`sqlite3` backup API — required for the
   `:memory:` case and for host visibility in Flatpak), spawn
   `bins.python_bin()` + worker (`flatpak_host_spawn` in Flatpak,
   `paths.no_window_kwargs()` on frozen Windows), forward output to the log.
   Failure → `[report] Export skipped: …` info line, run continues.
   The "Available:" message for an unknown format combines the static builtin
   list with the plugin list returned by the worker.

## C — `command` export

4. New export type in the `.tum`:
   `- command: {cmd: "mytool {db} {out}", …}`. Placeholders: `{db}` (temp
   sqlite copy), `{out}` (expanded path/file_name). Build argv with
   `shlex.split` + per-token `.format` (same pattern as the `editor_cmd`
   preference), run on the host (`bins.host_console_command()` /
   `flatpak_host_spawn`), `no_window_kwargs`. Non-zero exit → export-failed
   info line, run continues.

## Validation

5. `fake_exporter` stays a pip entry-point package but must be installed in
   the **host** python used by the suite: `pip install -e
   test/validation/fake_exporter` into the validation venv created by
   `test/validation/run.sh` (the one passed as `-d python_bin=…`); drop the
   install from `scripts/build_env.sh` if now redundant. The `report_plugin`
   item should then pass in **all** `--mode`s, not only source.
6. New validation item for the `command` export (portable command:
   `$(python_bin) -c "…"`).

## Docs

7. Rewrite the "Report exporters & plugins" section of `DESIGN.md`.
8. `release_note.txt`: custom report exporters now work in every install
   channel (pip install on the host); new `command` export to post-process
   the report with any external tool.
9. Manual (`doc/manual/sphinx/source/`): document both mechanisms in the
   report/export section.

## Facts checked (2026-07-23)

- Exporter contract: `__init__(name, con, path, pats, keys, no_header=False)`
  with a live sqlite connection; discovery at import of `test_report.py`.
- Without a `sqlite` export the DB is `:memory:` (`test_report.py`, `open()`)
  → temp-file materialization is mandatory for any out-of-process exporter.
- Flatpak manifest already grants `--filesystem=home`, `--filesystem=/tmp`,
  `--talk-name=org.freedesktop.Flatpak`.
- `report` item `PARAMS`: `export` is a free-form LIST — no schema constraint
  to extend.
- GUI `report_type` is a free string passed to `set_report` — no static
  format list to update.
