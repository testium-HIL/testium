# Testium — Claude Context

## What is testium

Testium is a test sequencer/runner written in Python. It executes YAML-based test scripts ("`.tum`" files) and supports two execution modes:

- **GUI mode** (default, no flag): PySide6 Qt application (`src/testium/main_win/`)
- **Batch mode** (`-b` / `--batch-execution`): headless, non-interactive, runs tests and exits

Run from repo root: `./run.sh` (Linux) or `run.bat` / `run.ps1` (Windows).  
Direct invocation: `python3 -m src/testium [-b] <test_file.tum>`

## Architecture

### Entry point
`src/testium/__init__.py` — parses CLI args, dispatches to the two modes.  
`multiprocessing.set_start_method('spawn')` is called early (required for Linux dialog subprocesses).

### Core execution
- `src/testium/interpreter/process.py` — `TestProcess(multiprocessing.Process)`: runs the test in a child process. Stdout is redirected via a `StringQueue` → pipe → parent thread (`capture_stdout`) that writes to real stdout.
- `src/testium/interpreter/batch.py` — `Batch`: parent-side orchestrator for `-b` mode. Creates the `msg_queue`, starts `TestProcess`, waits for the "finished" signal.
- `src/testium/interpreter/test_set.py` — `TestSet`: builds and executes the tree of test items.
- `src/testium/interpreter/test_items/test_item*.py` — one file per test item type (check, cycle, group, let, unittest, py_func, lua_func, console, git, dialogs, report, parallel, …).

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
`src/testium/interpreter/utils/termlog.py` — `TermLog` wraps stdout with colorama-based line coloring (PASS=green, FAIL=red, WARN=yellow, …). Applied in parent process for batch mode. Auto-detects light/dark terminal background via (in order): `COLORFGBG` env var, OSC 11 query, default dark.

### Dialog items in batch mode
All dialog items (`dialog_image`, `dialog_question`, `dialog_references`, `dialog_value`, `dialog_message`, `dialog_choices`, `dialog_note`) follow this rule in non-interactive text mode (`-b`):
- `auto_result` defined in the `.tum` → result controlled by it (`ok`/`yes` → SUCCESS, `cancel`/`no` → FAIL)
- `auto_result` absent → FAIL with `"Dialog not supported in batch mode"`
- `sleep dialog: true` → exception: just sleeps normally, no GUI, no failure

`auto_result` (and `auto_value` for value/note dialogs) is intended for the validation test suite (`test/validation/`) only.

### `parallel` item
`src/testium/interpreter/test_items/test_item_parallel.py` — runs multiple branches concurrently.

```yaml
- parallel:
    name: My parallel block
    sync: all        # all: wait for all; any: stop as soon as one finishes
    no_fail: true    # (optional) don't propagate branch failures to parent
    branches:
      - name: Branch A
        wait_for:              # (optional) poll condition before starting
          condition: <| expr |>
          timeout: 10
        steps:
          - ...
      - name: Branch B
        steps:
          - ...
```

- `TestItemParallel(TestItemContainer)`: mutates `dict_item["steps"]` to inject synthetic `parallel_branch` items so `load_test_recursively` loads branches normally as children.
- `TestItemParallelBranch(TestItemContainer)`: container for one branch. `wait_for` polls every 0.1s up to `timeout` seconds before running steps.
- `sync: any` calls `_stop_branch_recursively()` on all other branches when one *actually runs* (SUCCESS/FAILURE). A `NORUN` branch (disabled, condition not met) never wins the race.
- Each branch runs in a daemon thread; the parent waits with `.join()`.
- Branches stopped late (e.g. user disabled them in the GUI, or another sync:any branch already won) go through the normal `branch.stop() + branch.execute()` path so they always produce a clean DB entry via `addTest()`.
- Exceptions raised in a branch's `execute()` are caught by `run_branch`, logged to stdout, and converted to a `FAILURE` result so they never disappear silently.
- `sync: all` ignores `NORUN` branches when computing success (matches Group/Cycle semantics): only an actual `FAILURE` fails the parallel.
- `TestItemSleep` is interruptible (polls `self._is_stopped` in a loop) so `sync: any` can stop slow branches quickly. `py_func` and `console` items are not interruptible; their full duration is observed before the branch returns.

### `TestItemContainer` base class
`src/testium/interpreter/test_items/test_item_container.py` — shared base for Group, Cycle, Parallel, and ParallelBranch. Provides `_run_children_sequentially()` which handles stop-on-failure, `executedOnStop` items, and returns `(TestResult, stopped_bool)`.

### Report threading
`src/testium/interpreter/test_report/test_report.py` — SQLite report with thread-safe writes:
- `sqlite3.connect(..., check_same_thread=False)`
- `self._lock = threading.Lock()` guards the SQLite `INSERT` only.
- Per-item log capture (`stdio_redir.read()`) is naturally race-free thanks to per-thread buffers (see `StdoutProxy`).

### Thread-aware stdout (`StdoutProxy`)
`src/lib/stdout_redirect.py` — when `log_stored: True`, `intercept()` installs a `StdoutProxy` as `sys.stdout`/`sys.stderr` instead of a single shared `StringQueue`. The proxy:
- Holds one `StringQueue` per thread (registered via `register_thread(buffer=...)`). The main thread uses a default buffer; each parallel branch's thread registers its own at start and unregisters at end. `stdio_redir.read()` reads the calling thread's buffer → `addTest()` of an item running in branch X reads X's clean, non-interleaved output.
- For the live stream (terminal in batch / GUI panel), prefixes every line emitted from a branch's thread with `[<branch_name>] ` so concurrent branches stay readable.
- Exposes `write` / `writeln` / `flush` (Python 3.14's `unittest` calls `stream.writeln()` directly without `_WritelnDecorator`).

## Key files

| Path | Role |
|------|------|
| `src/testium/__init__.py` | CLI entry, mode dispatch |
| `src/testium/interpreter/batch.py` | `-b` mode orchestrator |
| `src/testium/interpreter/process.py` | Child test process |
| `src/testium/interpreter/test_set.py` | Test tree builder/executor |
| `src/testium/interpreter/test_items/test_item_container.py` | Base class for container items |
| `src/testium/interpreter/test_items/test_item_parallel.py` | `parallel` and `parallel_branch` items |
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

### `run` item
`src/testium/interpreter/test_items/test_item_run.py` — launches a `.tum` file in a new testium instance (`-b` in batch mode, `-r` in GUI mode). Result:
- **PASS** if the sub-instance launched and ran to completion (exit code is ignored)
- **FAIL** if the file is not found, `wait_for_exec` is set without `start_time`/`end_time`, the time window was not reached, or any other launch error

The sub-test's own pass/fail result is intentionally not propagated.

## Recent fixes / notable changes
- `parallel` item: new item with `sync: all|any`, `wait_for`, daemon threads, `_stop_branch_recursively()`. Each branch thread registers a per-thread stdout buffer with `stdio_redir.register_thread(...)` so its log capture and live-output prefix work in isolation.
- `parallel_branch` icon: distinct single-arrow icon (`parallel_branch.png`) separate from the parallel container's three-arrow icon.
- `parallel` F1 panel: `steps` stripped from each branch dict so the panel shows per-branch attributes without duplicating the tree.
- `test_item_container.py`: new `TestItemContainer` base class extracted from Group/Cycle patterns
- `test_item_sleep.py`: interruptible loop (checks `self._is_stopped`) instead of blocking `time.sleep()` so `sync: any` can stop slow branches quickly
- `stdout_redirect.py`: rewrote `intercept()` to install a `StdoutProxy` (thread-aware: per-thread capture buffers + branch-prefixed live output). Adds `writeln()` for Python 3.14 unittest compatibility.
- `test_report.py`: `check_same_thread=False` + lock around the SQLite `INSERT` for parallel branch concurrency. Log capture itself is race-free thanks to per-thread buffers.
- `terminal.py`: deleted — `-m`/`--terminal` mode removed.
- `batch.py`: premature loop exit when `gd_update` messages (no `"id"` key) were mistaken for the "finished" signal — fix: `"id" in m and m["id"] is None`
- `batch.py`: `control("loaded")` deadlock if `TestProcess` crashed before `cmd_th` started — fix: daemon thread + `threading.Event` + `is_alive()` polling
- `termlog.py`: `COLOR_DEFAULT = Fore.WHITE` invisible on light terminals; added auto-detection + light palette. Also fixed `write()` residue accumulation bug (`s[pos:]` → `s[pos+1:]`).
- Dialog items: `auto_result`/`auto_value` now used in non-interactive text mode; dialogs without `auto_result` FAIL immediately in batch mode.
- `run` item: renamed `tum_fime` → `tum`; removed `stdout=PIPE` (caused deadlock with `multiprocessing` spawn); result simplified to PASS on any completed subprocess.
- `unittest` item: renamed from `unittest_file` (cmd key, display name, Python constant `TYPE_UNITTEST_FILE` → `TYPE_UNITTEST`).
- GUI test tree: check and fold state preserved across same-file reloads (`test_file_manager.py`).
- Licence: EUPL-1.2 (`LICENSE`, `CONTRIBUTING.md`, `pyproject.toml`).

## Validation tests
Located in `test/validation/`. Run with `-b` flag:
```
./run.sh -b -l mon_log.log -- test/validation/main.tum
```
Parallel item tests: `test/validation/items/parallel/test.tum`

## Dependencies
See `src/requirements.txt`. Key ones: `pyside6`, `pyyaml`, `jinja2`, `colorama`, `gitpython`, `pexpect`, `matplotlib`.
