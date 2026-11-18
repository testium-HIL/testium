---
name: testium-validation
description: "How to run and extend the testium validation suite (test/validation/): run.sh and its modes (source/wheel/pyinstaller/flatpak/appimage), the per-channel pre-checks (lsp/schema/load_errors) and the source-only checks, the main.tum Jinja template, per-item tests (items/<name>/test.tum, param.yaml), the $(test)_PASS / $(test)_FAIL key convention, post_execution.py, and the validation venv. Use when adding or modifying a validation-suite test, running the suite, or debugging a suite failure."
---

# testium validation suite

One test set (`main.tum`) that exercises every testium feature, re-run against
every packaging channel. Use this skill when you add or modify a test in
`test/validation/`, run the suite, or debug a red run.

## Run it

```sh
./test/validation/run.sh                        # mode: source (default)
./test/validation/run.sh --mode wheel           # or pyinstaller | flatpak | appimage
./test/validation/run.sh clean                  # rebuild the venv first (must be the first arg)
./test/validation/run.sh --gui                  # through the GUI (-r -l <tmp log>), result printed at the end
```

- Windows: `test\validation\run.ps1` (source/wheel/pyinstaller only).
- Extra args are forwarded to testium (e.g. `-o` to strip colors).
- **The shell exit code is NOT the verdict.** This suite deliberately
  contains steps that must end FAIL (`$(test)_FAIL` negative tests), so
  testium's batch result — and therefore the script's exit code and the
  `Test run failed.` console line — is non-zero/failed on **every** run,
  green or not. Read the verdict from post-execution (see below).
- `set -e` stops at the first failing pre-check.
- Reports land in `test/tmp/validation-<mode>.sqlite` plus per-item
  `validation-<mode>-<item>.xml`, so modes don't clobber each other.
- wheel/pyinstaller/appimage need `./build_all.sh` first; flatpak needs the
  bundle installed.

## Pre-checks (run before the suite)

Per channel — they verify the build under test itself:

- `lsp_check.py` — `testium lsp` starts and `testium schema` works in this build.
- `schema_check.py` — the live schema is a valid draft 2020-12, matches the
  versioned `schema/tum.json` at the repo root, and accepts every fixture in
  `test/validation/schema/`. On a drift failure, regenerate with
  `testium schema > schema/tum.json`.
- `load_errors_check.py` — deliberately broken .tum files fail to load with a
  specific, located message (never a raw traceback).

Source-only — they import the interpreter/GUI directly and are skipped in the
other modes: `step_check`, `pause_jump_check`, `debug_output_check`,
`eval_expr_check`, `gd_restore_check`, `py_func_attach_check`,
`gui_reload_check`, `gui_state_check`, `gui_purity_check`,
`gui_presenter_check`, `settings_check`, `duration_check`. Each guards one
interpreter/GUI behavior (single-stepping, pause/jump, the debug toggle, F1
eval, global-dict restore, py_func attach, reload leaks, GUI state persistence,
toolkit-free presenter, settings merge, duration format).

## Anatomy

```
test/validation/
├── run.sh / run.ps1       launcher: modes, venv, pre-checks, launch
├── main.tum               Jinja template: one group per items/ subdirectory
├── param.yaml             suite config; `items` is auto-detected (os.scandir of items/)
├── post_execution.py      auto-invoked after the run (post_exec / post_exec_fail)
├── fake_exporter/         report-exporter plugin fixture (pip -e into the venv)
├── schema/                positive .tum fixtures for schema_check.py
├── load_errors/           broken .tum fixtures for load_errors_check.py
└── items/
    ├── <name>/test.tum    steps of item test <name> (Jinja allowed)
    ├── <name>/param.yaml  optional per-test config
    ├── <name>/*.py        optional py_func helper modules
    └── report.tum         shared, included after EVERY item test
```

- `main.tum` loops over `items`: it sets `test: <name>` and
  `test_path: items/$(test)`, then includes `items/<name>/test.tum` followed
  by `items/report.tum`. **Adding an item test = creating `items/<name>/`** —
  the list is auto-detected, nothing else to update.
- `$(test_directory)` = the directory of the main .tum (built-in global).
- The suite report (the `report:` block in main.tum) exports junit + sqlite
  into `$(validation_report_path)` (= `test/tmp/`, which must exist).

## PASS/FAIL convention

- Every step declares its expectation in `key`:
  - `key: $(test)_PASS` — the step must end PASS.
  - `key: $(test)_FAIL` — a negative test: the step must end FAIL. A FAIL here
    is the expected outcome and does not fail the run.
- `items/report.tum` (included after every item test) exports per-item
  text/html/junit reports keyed by `$(test)_PASS` / `$(test)_FAIL`, so a
  `py_func` step can inspect the generated files right after the export.
  Cross-item checks belong there, gated with
  `condition: <| "$(test)" == "<name>" |>`.
- After the run, testium auto-invokes `post_execution.py` (same directory as
  main.tum): `post_exec` when the run succeeded, `post_exec_fail` otherwise —
  both run the same check. It reads the sqlite report and counts a failure for
  every `<test>_PASS` row that ended FAIL and every `<test>_FAIL` row that
  ended PASS, and writes per-item junit XML next to the sqlite.
- **The verdict is post-execution `Post execution finished : SUCCESS`, not the
  batch exit code.** A suite failure must come from a `$(test)_PASS` step that
  actually FAILs during the run (or a `$(test)_FAIL` step that PASSes);
  intentional negative tests always make the batch result "failed" and the
  exit code non-zero, even on a green run.
- Quick verdict check in `test/tmp/validation-<mode>.sqlite` (table `tests`,
  columns `report_key`, `result`):
  `SELECT test_name, report_key, result FROM tests WHERE
  (report_key LIKE '%_PASS' AND result NOT IN ('PASS','SKIP')) OR
  (report_key LIKE '%_FAIL' AND result <> 'FAIL')` — empty = green.

## Add an item test (recipe)

1. `mkdir items/<name>`; write `test.tum` — a YAML list of steps, each with a
   `name` and a `key: $(test)_PASS` or `key: $(test)_FAIL`. Jinja branching on
   `$(os)` is how the suite stays cross-platform (see the console tests).
2. Optional `param.yaml` for test-specific config. Note: **every**
   `items/*/param.yaml` is loaded into the suite config by main.tum, so keys
   are global to the run — don't create collisions.
3. Optional helper module in the same directory; call it with
   `py_func: {file: $(test_path)/<mod>.py, func_name: ...}`. The module must
   `import py_func.tm as tm` and must never import `api.testium` /
   `interpreter.*`.
4. Cross-item checks (e.g. inspecting a generated report): add a step in
   `items/report.tum` with `condition: <| "$(test)" == "<name>" |>`.
5. If the test exercises a new item, parameter or action: update the docs and
   regenerate `schema/tum.json` (`testium schema > schema/tum.json`) —
   `schema_check.py` fails on drift.
6. Run `./test/validation/run.sh` (source mode). Green = every pre-check OK
   and post-execution prints `SUCCESS`.

## Pitfalls

- Item test files may be Jinja (`{% if os == "Windows" %}`); schema
  validation does not apply to them (files containing `{%` or `{{` are
  skipped) — it only covers the plain fixtures in `test/validation/schema/`.
- Console tests: open `console_name: term` with
  `terminal_path: $(test_directory)`; `exec` handles the completion marker for
  shell dialects; for device-like behavior use `dialect: none` plus
  `writeln`/`read_until`.
- Venv: every test-execution subprocess (inline `<| ... |>`, `py_func`,
  `cycle`, `post_execution`) runs in `${TMPDIR:-/tmp}/testium-validation-venv`,
  pinned via `-d python_bin=...`; the `venv` item asserts this. `fake_exporter`
  is pip-installed into it for the `report_plugin` item. `clean` rebuilds the
  venv (use after a system Python upgrade).
- `report` export `path`s must exist before the run — testium does not create
  them; `test/tmp/` is the suite's report home.
