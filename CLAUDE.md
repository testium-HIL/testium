# Testium — Claude Context

## What is testium

Testium is a test sequencer/runner written in Python. It executes YAML-based test scripts ("`.tum`" files) and supports three execution modes:

- **GUI mode** (default, no flag): PySide6 Qt application (`src/testium/main_win/`)
- **Batch mode** (`-b` / `--batch-execution`): headless, non-interactive, runs tests and exits
- **Terminal mode** (`-m` / `--terminal`): interactive REPL in the terminal (partially implemented / work-in-progress)

Run from repo root: `./run.sh` (Linux) or `run.bat` / `run.ps1` (Windows).  
Direct invocation: `python3 -m src/testium [-b|-m] <test_file.tum>`

## Architecture

### Entry point
`src/testium/__init__.py` — parses CLI args, dispatches to the three modes.  
`multiprocessing.set_start_method('spawn')` is called early (required for Linux dialog subprocesses).

### Core execution
- `src/testium/interpreter/process.py` — `TestProcess(multiprocessing.Process)`: runs the test in a child process. Stdout is redirected via a `StringQueue` → pipe → parent thread (`capture_stdout`) that writes to real stdout.
- `src/testium/interpreter/batch.py` — `Batch`: parent-side orchestrator for `-b` mode. Creates the `msg_queue`, starts `TestProcess`, waits for the "finished" signal.
- `src/testium/interpreter/test_set.py` — `TestSet`: builds and executes the tree of test items.
- `src/testium/interpreter/test_items/test_item*.py` — one file per test item type (check, cycle, group, let, unittest, py_func, lua_func, console, git, dialogs, report, …).

### Communication channels (parent ↔ child process)
- `msg_queue` (`multiprocessing.Queue`): carries status messages from child to parent.
  - Item status: `{"id": <non-None>, "name": ..., "status": "started"|"finished", ...}`
  - Global dict updates: `{"type": "gd_update"|"gd_delete", "key": ..., "value": ...}` — **no "id" key**
  - Process finished: `{"id": None, "name": "test_process", "status": "finished"}` — id key present but `None`
- `tst_ctrl` (`TestSetController`): sends control commands (execute, stop, pause, close, …) from parent to child.
- stdout pipe (`multiprocessing.Pipe`): streams test output from child back to parent's `capture_stdout` thread.

### Stdout pipeline (batch mode)
```
test item print()
  → sys.stdout (StringQueue, in child)
  → send_stdout thread (child) → pipe → capture_stdout thread (parent)
  → print() → sys.stdout (TermLog wrapping real stdout, in parent)
  → terminal
```

### Global dictionary
`src/testium/interpreter/utils/globdict.py` — shared state accessible from test scripts via `tm.gd()` / `tm.setgd()`. When `set_update_queue()` is active (during test execution), every `setgd`/`delgd` on a non-`_`-prefixed key pushes a message to `msg_queue`.

### Coloring (`-o` disables it)
`src/testium/interpreter/utils/termlog.py` — `TermLog` wraps stdout with colorama-based line coloring (PASS=green, FAIL=red, WARN=yellow, …). Applied in parent process for batch/terminal modes. Auto-detects light/dark terminal background via (in order): `COLORFGBG` env var, OSC 11 query, default dark.

### Dialog items in batch mode
All dialog items (`dialog_image`, `dialog_question`, `dialog_references`, `dialog_value`, `dialog_message`, `dialog_choices`, `dialog_note`) follow this rule in non-interactive text mode (`-b`):
- `auto_result` defined in the `.tum` → result controlled by it (`ok`/`yes` → SUCCESS, `cancel`/`no` → FAIL)
- `auto_result` absent → FAIL with `"Dialog not supported in batch mode"`
- `sleep dialog: true` → exception: just sleeps normally, no GUI, no failure

`auto_result` (and `auto_value` for value/note dialogs) is intended for the validation test suite (`test/validation/`) only.

## Key files

| Path | Role |
|------|------|
| `src/testium/__init__.py` | CLI entry, mode dispatch |
| `src/testium/interpreter/batch.py` | `-b` mode orchestrator |
| `src/testium/interpreter/process.py` | Child test process |
| `src/testium/interpreter/terminal.py` | `-m` mode (WIP) |
| `src/testium/interpreter/test_set.py` | Test tree builder/executor |
| `src/testium/interpreter/utils/globdict.py` | Global variable dict |
| `src/testium/interpreter/utils/termlog.py` | Terminal color output |
| `src/lib/stdout_redirect.py` | `StdioRedirect` singleton (`stdio_redir`) |
| `src/lib/string_queue.py` | Thread-safe string buffer used for stdout redirection |
| `src/testium/libs/testium.py` | Public API for test scripts (`tm.*`) |

## GUI icons (main_win)

Icons live in `src/testium/main_win/resources/` with three theme variants:

| Folder | Theme index | Usage |
|--------|-------------|-------|
| `color/` | 0 (default) | Coloured icons |
| `black/` | 1 | Black silhouette on transparent |
| `white/` | 2 | White silhouette on transparent (LA mode) |

Icons are **64×64 PNG**. Black variants: RGBA with RGB=`(0,0,0)`, alpha varies. White variants: LA with luminance=`255`, alpha varies.

The mapping item-type → icon filename is in `_ITEM_CONFIG` (`src/testium/main_win/test_tree_items/test_tree_item.py`). At runtime, `icon_prefix()` returns `:/color`, `:/black`, or `:/white` (Qt resource prefix) based on the user preference.

All icons must be declared in `src/testium/main_win/resources/testium_core_win.qrc` (one entry per theme section). After any QRC change, regenerate the compiled resource file:
```
cd src/testium/main_win/resources
pyside6-rcc testium_core_win.qrc -o testium_core_win_rc.py
```

Icons are assigned once when the test file is loaded (not updated live on theme change — a file reload is required).

## Known issues / WIP
- `-m` (terminal mode) is not functional yet.
- `text_no_pyside` branch: work in progress on text mode improvements.

### `run` item
`src/testium/interpreter/test_items/test_item_run.py` — launches a `.tum` file in a new testium instance (`-b` in batch mode, `-r` in GUI mode). Result:
- **SUCCESS** if the sub-instance launched and ran to completion (exit code is ignored)
- **FAILURE** if the file is not found, `wait_for_exec` is set without `start_time`/`end_time`, the time window was not reached, or any other launch error

The sub-test's own pass/fail result is intentionally not propagated.

## Recent fixes (branch `text_no_pyside`)
- `batch.py`: premature loop exit when `gd_update` messages (no `"id"` key) were mistaken for the "finished" signal — fix: `"id" in m and m["id"] is None`
- `batch.py`: `control("loaded")` deadlock if `TestProcess` crashed before `cmd_th` started — fix: daemon thread + `threading.Event` + `is_alive()` polling
- `termlog.py`: `COLOR_DEFAULT = Fore.WHITE` invisible on light terminals; added auto-detection + light palette. Also fixed `write()` residue accumulation bug (`s[pos:]` → `s[pos+1:]`).
- Dialog items: `auto_result`/`auto_value` now used in non-interactive text mode; dialogs without `auto_result` FAIL immediately in batch mode.
- `run` item: removed `stdout=PIPE` (caused deadlock with `multiprocessing` spawn); simplified result to SUCCESS on any completed subprocess.

## Validation tests
Located in `test/validation/`. Run with `-b` flag against each `.tum` file.

## Dependencies
See `src/requirements.txt`. Key ones: `pyside6`, `pyyaml`, `jinja2`, `colorama`, `gitpython`, `pexpect`, `matplotlib`.
