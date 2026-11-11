# Testium manual ↔ implementation consistency report

Scope: `doc/manual/sphinx/source/*.rst` (+ `test_items/*.rst`) vs `src/testium/`
(stale `src/build/`, `src/dist/`, `__pycache__` ignored).

> **Build env note (PDF):** `build_doc.sh` failed on TeX Live 2026.1 (Arch)
> because Sphinx 9.2.0's `sphinxlatextables.sty` pins `array[=v2.6]`, but the
> installed `array` (v2.6n) declares no `v2.6` label (the rollback file
> `array-2024-06-01.sty` only exists in the texlive-dev tree). Local 1-line
> patch applied to
> `test/tmp/.venv/.../sphinx/texinputs/sphinxlatextables.sty` (load `array`
> unpinned). Re-apply if `build_all.sh` reinstalls sphinx.

## ✅ Coverage — no missing test items

All 23 manual test items map 1:1 to implementation classes with matching YAML
keys (`TestItemType` in `interpreter/utils/constants.py`): unittest, pytest,
console, loop, py_func, lua_func, report, git, plot, group, dialog_image,
dialog_message, dialog_note, dialog_question, dialog_references, dialog_value,
dialog_choices, let, check, sleep, run, json_rpc, parallel.

`schema/tum.json` contains exactly these (plus actions/params); its top-level
keys (`config_file`, `main`, `report`) match the manual.

---

## ❌ Discrepancies — manual contradicts implementation

| # | Topic | Manual says | Implementation does | Where |
|---|-------|-------------|---------------------|-------|
| 1 | CLI | usage header `testium.pyw` | entry point is `testium` (`[project.scripts] testium = "testium:main"`); no `.pyw` exists | `cdl_interface.rst` L6 vs `src/pyproject.toml` |
| 2 | CLI `-g` | usage block: `-g` "GUI debug mode" | flags are `-g, --dev-debug, --debug`, "attach a debugger to testium itself (development…)" — the manual's own detailed section (`--dev-debug`) is correct; usage block is stale | `cdl_interface.rst` vs `__init__.py` argparse |
| 3 | Report export `path` default | `$(report_path)` | default `''`, falling back to preference `defaultReportPath` = `$(test_directory)`. `report_path` is **not** a global variable | `reports.rst` vs `test_report.py` `Export`, `settings.py` L47 |
| 4 | plot `last_value` | stored in `plv_<item_name>` (example `$(plv_Plot measure_1 value)`) | stored in `plv_<plot_name>` (`tm.setgd("plv_" + gname)`) | `plot_test_item.rst` vs `test_item_runtime_plot.py` L242 |
| 5 | console `write_delay` | documented as an item-level attribute | it is a parameter of the `open` action only | `console_test_item.rst` vs `test_item_console.py` |
| 6 | console `open.log` | "only for Telnet and Serial" | applied generically to all protocols | `console_test_item.rst` vs `test_item_console.py` |
| 7 | console `terminal_path` | "Path of the terminal console" | "Working directory for the local terminal protocol" | `console_test_item.rst` vs `test_item_console.py` L85 |
| 8 | json_rpc `timeout` | listed without required marker | `required=True` | `json-rpc_test_item.rst` vs `test_item_json_rpc/__init__.py` |
| 9 | loop `loop_index_inverse` | "starts from the iteration count minus 1 and decrements" (9…0 for 10 iterations) | computes `_niter - i - 1` → **8…-1** (off-by-one) | `loop_test_item.rst` L79 vs `test_item_cycle.py` L158 + `params.py` `getInverseLoopIndex` |
| 10 | loop `exit_condition` function | "must have two parameters: the current loop iterator value and the report" | called with **one** argument — the current loop value (or a custom `param` list) | `loop_test_item.rst` L50-53 vs `test_item_cycle.py` L227-242, `py_func_exec.py` `func_call` |
| 11 | dialog_choices `auto_result` | "Selection used in batch mode (choice path or label)" | it is a truthy gate: any set non-`cancel` value ⇒ **all choices checked**; the value is never parsed as a selection | `dialog_choices_test_item.rst` L70-71 vs `test_item_choices_dialog.py` L88-98 + `dialog_presenter.accepts` |
| 12 | dialog_references `reference` | "``question`` and ``reference`` are mandatory" | only `question` is required; without `reference` the dialog shows a single empty row | `dialog_reference_test_item.rst` L34 vs `test_item_tested_references.py` L28-30 |

Minor wording: the `skipped` common attribute is described as if a skipped
step "fails"; it is reported as SKIP/NORUN. — **done**
(`items_common_attributes.rst`, 2026-11-11): reworded to "displayed as
skipped (``SKIP``) in the report" (code: `TestValue.NORUN` → `SKIP`).

Additional finding (not in the original audit): `test_name` is the `name`
attribute of the `main` section (default `Unnamed`), not the file name
(`process.py` L175-176). — **done** (`tum_syntax.rst`, 2026-11-11).

---

## ➕ Implemented but undocumented

1. **Built-in globals** — implementation sets six keys absent from the manual's
   built-in list (`test_init.py` L158-167, L259-269): `testium_version`,
   `testium_path`, `config_files`, `test_version`, `test_modifs`,
   `start_test_date`.
2. **`!raw_include`** — non-recursive include tag (`include.py` L98-101), no
   mention anywhere in the manual.
3. **`include_directory`** jinja variable — injected into every template render
   (`template.py` L99-100), undocumented.
4. **`overwrite_log`** (console `open`, default True) — undocumented.
5. **`param`** (loop `exit_condition`, replaces the default `[loop_param]`
   argument) — undocumented.
6. **`param`** (plot `periodic` action, args passed to the periodic function
   each call) — undocumented.

---

## ✏️ Manual-internal defects

- `home` is listed **twice** in the built-in values list (`tum_syntax.rst` L132 & L138).
- Common-attributes table writes the key attribute as `Key` (capitalized) — typo.
- `tum_syntax.rst` L85: `:ref:`lua<sec_py_func_item>`` — the lua link points to the py_func anchor.
- Default config file: implementation auto-loads `param.yaml` **or** `param.yml`
  (`process.py` L92-99); manual only mentions `param.yaml`.
- Copy-paste artifacts: `dialog_message`, `dialog_note`, `dialog_question`
  examples all use `name: dialog value test item`; json-rpc section titled
  "jsonrpc" while the YAML key is `json_rpc`; the `-g` usage-block help (see #2)
  and CLI option order differ from the argparse definition.

---

## 📎 Stale *implementation* docstrings (not manual bugs, footnotes)

- `api/testium.py` `text_mode()` docstring mentions a terminal `-m` flag that
  does not exist in argparse.
- `test_item_choices_dialog.py` `choices` docstring says "a list of strings,
  or a nested mapping {label: subchoices}" — the runtime actually requires a
  list of `{name: …}` dicts (the **manual** is correct here).

---

## ✅ Verified consistent (no action needed)

- CLI flag set, `--version`, `-t {sqlite,json,junit,html,text}` vs `REP_TYPES`;
  `-d` defines override order; `run` item GUI `-r` / batch `-b -o` / auto
  log-file naming / time windows.
- Reports: root `report` element (`enabled`, `log_stored`, `export`), inline
  `report` item (required `export`, sqlite ignored, no header), DB schema
  (9 header fields, 12 `tests` columns in the manual's order), duration in
  0.1 ms units, NORUN→SKIP mapping, custom exporter plugin mechanism.
- Common attributes: full `COMMON_PARAMS` set matches the manual table;
  `store_result`, `process_result`, `expected_result`, `condition`,
  `report` semantics.
- Duration format `Nd Nh Nm Ns` (order enforced, negatives refused) vs `duration.py`.
- Loop: `iterator` int/list/undefined→`inf`, `loop_param`/`loop_index`/`loop_count`
  (incl. `inf`), `exit_condition.time` in minutes, `value` exit, `file`+`func_name` pairing rules.
- py_func/lua_func: `file`, `func_name`, `param`, `context_id`, `debug`
  (debugpy, `py_func_debug_port` default 5678, py_func only); `python_env`/`lua_env`
  honored in `py_process.py`/`lua_process.py`.
- console: `console_instances`, `cn_<name>` (parent-item name), `read_until`
  (expected/regex/timeout/mute), `exec` (cmd/timeout/mute), protocols telnet/
  ssh/serial/rawtcp/terminal and their params.
- json_rpc: console/udp adapters (`server`, `snd_port`, `rcv_port`, `bufsize` 1450,
  `multicast_if`; console `name`+`prompt`), actions open/close/query/receive,
  version default "1.0", `rand` id prefix, mute.
- parallel: `sync` all/any, `wait_for` (condition, timeout 30, 0.1 s polling,
  timeout→branch FAIL).
- Dialogs: `auto_result`/`auto_value` semantics for image/message/note/
  question/value; `cs_<name>` structure `{name, checked, choices}`;
  `tested_items` list-of-`{reference, revision, serial}` with `/` pre-fill.
- Templates/includes: main file always jinja-processed, config+built-in
  variables, include args passed as declared, `expand()` load-time resolution,
  `!include` with/without `file:` mapping, root `config_file` key (string or list).

---

## 📋 Plan of action (prioritized)

### P0 — Likely to mislead users in scripts
- [x] **[3]** Report export `path` default: fixed the table — `$(report_path)`
  (nonexistent global) → `/`, and documented the real behavior: when empty
  (the default) the file is written from `file_name` as a relative path; no
  `defaultReportPath` fallback for export entries (that fallback only exists
  in `extractReportPath()` for the root `report:` element) — **done**
  (`reports.rst`, 2026-11-11; PDF regenerated, p. 55).
- [x] **[4]** plot `last_value`: correct `plv_<item_name>` → `plv_<plot_name>` in
  the manual and example — **done** (`plot_test_item.rst`, 2026-11-11; PDF
  regenerated, Listing 4.43).
- [x] **[9]** Loop `loop_index_inverse`: fixed the code off-by-one — the manual
  ("count-1 … 0") is the intended contract (mirror of `loop_index`, never
  negative); `test_item_cycle.py` L158 `_niter - i - 1` → `_niter - i`; added
  regression test (`items/cycle`: `iterator: 5`, asserts
  `loop_index_inverse == 4 - loop_index` each cycle; failed on iteration 1
  with the old code) — **done** (2026-11-11; full source validation suite:
  post-execution SUCCESS).
- [x] **[10]** Loop `exit_condition` function signature: corrected the false
  "two parameters (loop value, report)" claim → single argument by default
  (`$(loop_param)`); added the missing `param` attribute bullet — **done**
  (`loop_test_item.rst`, 2026-11-11; PDF regenerated, pp. 35-36).

### P1 — Contract mismatches
- [x] **[11]** dialog_choices `auto_result`: removed from the manual (internal
  validation-suite gate, not a user contract) — dropped the `auto_result`
  bullet on **all 7 dialog pages** (choices, image, message, note, question,
  references, value) plus the `auto_value` bullets on note/value, and fixed
  "specific attribute:" → "attributes" in `dialog_value`; rewrote the 7
  `auto_result`/`auto_value` PARAMS docstrings with the real contract
  (unattended-run gate: text-mode per-dialog semantics + GUI `ok`/`yes`
  auto-accept after 2 s / anything else auto-rejects); regenerated
  `schema/tum.json` via `./run.sh schema` (diff = exactly the 7 descriptions)
  — **done** (2026-11-11; PDF pp. 22-26 verified; full source validation
  suite: schema check PASS, post-execution SUCCESS).
- [x] **[12]** dialog_references: `reference` is documented as optional (single
  empty row when absent), not mandatory — **done** (`dialog_reference_test_item.rst`,
  2026-11-11; PDF p. 25 verified; full source validation suite: post-execution
  SUCCESS).
- [x] **[5]** console `write_delay`: moved out of the item-level attribute list
  into the `open` action bullets, with a note that the `ssh` protocol does not
  apply it (`SshConsole.__init__` takes no `write_delay`) — **done**
  (`console_test_item.rst`, 2026-11-11).
- [x] **[6]** console `open.log`: rewritten — accepted by every protocol, but
  the log is only written for `telnet`/`serial` (the others print
  "logging of <protocol> is not yet supported" and ignore it); a path ending
  in `.log` names a file, otherwise it names a folder (created if missing)
  holding `<folder>/<console_name>.log` — **done** (`console_test_item.rst`,
  2026-11-11; PDF p. 23 verified).
- [x] **[7]** console `terminal_path`: description fixed to "Working directory
  for the local terminal protocol" — **done** (`console_test_item.rst`,
  2026-11-11; PDF p. 23 verified).

### P2 — Missing documentation (implemented but undocumented)
- [x] **[19]** Built-in globals: added `testium_version`, `testium_path`,
  `config_files`, `test_version`, `test_modifs`, `start_test_date` — **done**
  (`tum_syntax.rst`, 2026-11-11; PDF p. 15 verified).
- [x] **[20]** `!raw_include` — documented in `includes.rst` (verbatim splice,
  no sub-sequence wrapper, no source-file attribution; verified by an isolated
  loader experiment) — **done** (2026-11-11). **[21]** `include_directory`
  jinja variable — subsection added to `templates.rst` (dir of the file being
  rendered, main + included files) — **done** (2026-11-11; PDF p. 49 verified).
- [x] **[6/23]** `overwrite_log` (bullet after `log`, `console_test_item.rst`);
  loop `exit_condition.param` (already documented from **[10]**, nothing to do);
  plot `periodic.param` (bullet between `func_name` and `eval`,
  `plot_test_item.rst`) — **done** (2026-11-11).
- [x] **[8]** json_rpc `timeout`: item-level `timeout` marked `required.`
  (item-level `required=True`; the `query`/`receive` action timeouts stay
  `default=None`) — **done** (`json-rpc_test_item.rst`, 2026-11-11).

### P3 — Manual-internal defects & stale docstrings
- [x] **[1]** CLI: usage header `testium.pyw` → `testium` — **done**
  (`cdl_interface.rst:6`, 2026-11-11).
- [x] **[2]** CLI: usage block — replaced the whole stale block with the real
  `testium --help` output (verified byte-identical: `-o` after `-b`,
  `-t {sqlite,junit,json,html,text}` order, `options:` header, aligned `-c`,
  `-g, --dev-debug, --debug` + dev-debug help) — **done** (`cdl_interface.rst`,
  2026-11-11; PDF regenerated via `build_doc.sh`).
- [x] Remove duplicate `home` bullet (`tum_syntax.rst`) — **done** (2026-11-11).
- [x] Fix `Key` → `key` in common attributes table — **done** (2026-11-11).
- [x] Fix lua `:ref:` anchor → `sec_lua_func_item` (`tum_syntax.rst`) — **done**
  (2026-11-11).
- [x] Mention `param.yml` for the default config file (the code loads **both**
  `param.yaml` and `param.yml` that exist, in that order — `process.py` L92-99)
  — **done** (2026-11-11).
- [x] Fix dialog `name:` copy-paste artifacts (`dialog_message`/`dialog_note`/
  `dialog_question` examples, 1 commit) and the json-rpc section title +
  item-name references → `json_rpc` (protocol mentions like "jsonrpc
  server/frame/action" left as-is) — **done** (2026-11-11).
- [x] Update stale implementation docstrings: `api/testium.py` `text_mode()`
  (dropped the nonexistent `-m` flag — only `-b` enables text mode) and
  `test_item_choices_dialog.py` `choices` (a list of `{name: …}` mappings);
  `schema/tum.json` regenerated (diff = exactly that one description) —
  **done** (2026-11-11).
