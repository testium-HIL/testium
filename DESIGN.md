# Testium — Design Context

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
`src/testium/runtime/stdout_redirect.py` — when `log_stored: True`, `intercept()` installs a `StdoutProxy` as `sys.stdout`/`sys.stderr` instead of a single shared `StringQueue`. The proxy:
- Holds one `StringQueue` per thread (registered via `register_thread(buffer=...)`). The main thread uses a default buffer; each parallel branch's thread registers its own at start and unregisters at end. `stdio_redir.read()` reads the calling thread's buffer → `addTest()` of an item running in branch X reads X's clean, non-interleaved output.
- For the live stream (terminal in batch / GUI panel), prefixes every line emitted from a branch's thread with `[<branch_name>] ` so concurrent branches stay readable.
- Exposes `write` / `writeln` / `flush` (Python 3.14's `unittest` calls `stream.writeln()` directly without `_WritelnDecorator`).

### Subprocess API contract (py_func / lua_func)

User test scripts running inside a `py_func` or `lua_func` subprocess **must** use the JSON-RPC bridge to interact with testium state:

- Python: `import py_func.tm as tm` — auto-generates wrappers for every function in `runtime/api.py:SUPPORTED_API`. `tm.gd`/`tm.setgd`/`tm.delgd` go through JSON-RPC to the parent.
- Lua: `local tm = require("tm")` — same idea on the Lua side.

`api.testium` is the *main-process* implementation; it is **not** exposed to subprocesses by design (not bundled in PyInstaller, not on the subprocess `PYTHONPATH` in pip-installed mode either when isolation is preserved). An import attempt from a subprocess script is a code smell and is detected by `test/validation/items/isolation/`.

To add a new API call usable from subprocesses:
1. Add the function to `api/testium.py`
2. Add its name to `SUPPORTED_API` in `runtime/api.py`
3. It is auto-exposed via JSON-RPC by `interpreter/utils/api_srv.py` and auto-wrapped by `py_func/tm.py:_make_api`

### External interpreter resolution (`bins.py`)
`src/testium/interpreter/utils/bins.py` — single source of truth for the paths to the external Python and Lua interpreters used by subprocesses.

- `python_bin()` / `lua_bin()` : resolve and cache. The cache is keyed by `(name, override)` so that a later change to `gd[python_bin]` (typically when a `param.yaml` sets the key) triggers a re-resolution on the next lookup instead of returning the stale auto-discovered path. Falls back to discovery on PATH (candidates: `python3`/`python` and `lua`/`lua5.5`/`lua5.4`/`lua5.3`/`lua5.2`/`lua5.1`).
- `ensure(*names)` : called by `TestSet._validate_runtime_deps()` at test load. Always requires `python` (the eval engine always runs); requires `lua` only if a `lua_func` item is in the tree. Fails fast with a clear error citing tried candidates and override key.

Engines (`PyProcessBase`, `LuaProcessBase`, `EvalExecEngine`) call `bins.python_bin()`/`bins.lua_bin()` themselves — call sites never pass an explicit binary path.

#### Override-timing contract (`apply_overrides`)
`bins.python_bin()` is called for the **first** time inside `eval_process_init()` (the long-lived inline-`<| … |>` subprocess), which happens **before** the YAML param files are loaded. To make `-d python_bin=…` and the GUI `python_bin` preference take effect for `eval_proc` itself, `process.py:run()` applies them to gd **before** `eval_process_init()` via the `apply_overrides()` helper extracted from `update_global()`. The post-load `update_global()` call then re-applies the same overrides (after `prepare_global()` clears gd), keeping the gd value in sync with the cached resolution.

| Override source | `eval_proc` | `py_func` / `cycle` / `post_exec` |
|---|---|---|
| `-d python_bin=…` (CLI) | ✅ | ✅ |
| GUI `python_bin` preference | ✅ | ✅ |
| `python_bin: …` in `param.yaml` | ❌ (eval_proc already started) | ✅ (cache re-resolves on key change) |

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
| `src/testium/runtime/stdout_redirect.py` | `StdioRedirect` singleton (`stdio_redir`) |
| `src/testium/runtime/string_queue.py` | Thread-safe string buffer used for stdout redirection |
| `src/testium/api/testium.py` | Public API for test scripts (`tm.*`) |
| `src/testium/py_func/` | Python subprocess for `py_func` items (sandboxed: imports only `runtime/` and `py_func/`) |
| `src/testium/lua_func/` | Lua subprocess scripts for `lua_func` items |

## Package layout

The whole project is a single Python package under `src/testium/`:

```
src/testium/
├── __init__.py / __main__.py
├── runtime/      internal plumbing (jrpc, stdout_redirect, string_queue, tum_except, api)
├── api/          public SDK exposed to test scripts (`import api.testium as tm`)
├── interpreter/  test execution engine (NOT visible to py_func/lua_func)
├── main_win/     GUI (NOT visible to py_func/lua_func)
├── py_func/      subprocess code for python_func items
└── lua_func/     subprocess scripts for lua_func items (data files)
```

`subproc_path()` and `testium_path()` both return the package directory. The py_func subprocess is launched with cwd=that directory and `python3 py_func`. The contract that `py_func/` and `lua_func/` only depend on `runtime/` (no `interpreter`, `main_win`, `api`, `testium`) is enforced by `test/validation/items/isolation/`.

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

The interpreter and entry point used to spawn the sub-instance are picked automatically by `_testium_launch_cmd()` based on how the parent was started (AppImage → `$APPIMAGE`; Flatpak → `flatpak run`; PyInstaller → the frozen binary; source/wheel → `[sys.executable, abspath(sys.argv[0])]`). The user cannot override either via the YAML — selecting a different testium binary or Python from a sub-test was removed because it was either ill-defined (bundle modes have no separable Python) or could mismatch the parent's environment in surprising ways.

### Report exporters & plugins
`src/testium/interpreter/test_report/test_report.py` — `_EXPORTER_REGISTRY` dict maps a format name (cmd key in the YAML `report.export`) to a lazy loader. Built-ins: `text`, `json`, `junit` (needs `junit_xml`), `html` (needs `lxml`). `sqlite` is the storage layer, no-op as an export.

Third-party plugins are discovered at module import via `importlib.metadata.entry_points(group="testium.exporters")` — installing a wheel that declares such an entry point is enough, no testium config change needed:
```toml
[project.entry-points."testium.exporters"]
my_format = "my_pkg:MyExporter"
```
Exporter contract: `__init__(self, name, con, path, pats, keys, no_header=False)` — the class does its work in `__init__` and writes to `path`.

Behaviour on errors:
- Unknown format → info line `[report] Export skipped: format "X" not found. Available: ...`, run continues.
- Optional dependency missing → same info line with a pip-install hint, run continues.

A real-world test plugin lives at `test/validation/fake_exporter/` (CSV exporter, auto-installed by `scripts/build_env.sh` and exercised by `test/validation/items/report_plugin/`).

## Packaging

Four distribution channels coexist, all sharing the single `src/testium/` package and the single `src/requirements.txt` dependency list:

| Channel | Where | Build | Notes |
|---------|-------|-------|-------|
| Wheel (`pip install`) | `src/pyproject.toml` | `python -m build` | Vanilla Python package; entry point `testium = "testium:main"`. |
| PyInstaller binary | `package/pyinstaller/` | `build.sh` | Single ~130 MB binary. `py_func`, `runtime`, `lua_func` bundled at `_MEIPASS` root so the **host** Python can find them when launched as `python3 py_func`. `api`/`interpreter` are **not** exposed (subprocess isolation). |
| Flatpak | `package/flatpak/` | `build.sh` (uses `flatpak-builder`) | KDE 6.10 runtime. The bundled Python runs only the main process; `py_func` / `lua_func` MUST run under the **host** interpreter (no Python/Lua bundled). Produces a distributable `.flatpak` bundle. |
| AppImage | `package/appimage/` | `build.sh` (Debian Bookworm container via Podman/Docker) | Bundles Python 3.11 for the main process; `py_func` / `lua_func` MUST run under the **host** interpreter. Build runs in a container so it works on Arch / any non-Debian host. |

The `.deb` work-in-progress lives in `package/deb/`:
- `test_distro.sh debian:bookworm | debian:trixie | ubuntu:24.04` spins up a Docker/Podman container, reports system package availability, falls back to pip for what's missing (`pyside6` on bookworm/ubuntu, `telnetlib3`, `junit_xml`), runs the validation suite. Currently green on the three targets.

### Host-only py_func / lua_func in sandboxed bundles (Flatpak, AppImage)

The bundled Python (Flatpak's runtime python, AppImage's `python3.11`) is reserved for the **main process only**. Subprocesses (`py_func`, `lua_func`, `git`, the `run` item's sub-instance) must use the host's interpreters and tools so user-installed modules (pyserial, junit_xml, …) are visible. This is enforced by `interpreter/utils/bins.py`:

- `_in_flatpak()` (checks `/.flatpak-info`) and `_in_appimage()` (checks `APPIMAGE` env var) detect the sandbox.
- **Flatpak**: the sandbox glibc/ABI is incompatible with arbitrary host shared libraries, so we **cannot** run host binaries inside the Flatpak runtime — `LD_LIBRARY_PATH` injection trips a `_dl_call_libc_early_init` assertion. The supported way out is `flatpak-spawn --host`, a stub on `$PATH` inside every Flatpak that proxies an `exec` over D-Bus to the host's `org.freedesktop.Flatpak` service. The manifest grants `--talk-name=org.freedesktop.Flatpak` so the call is allowed. Helpers:
  - `flatpak_host_spawn(interp, args, host_cwd, extra_env=…)` builds the spawn command vector with a curated set of forwarded env vars (`HOME`, `USER`, `DISPLAY`, `DBUS_SESSION_BUS_ADDRESS`, …) plus any explicit overrides.
  - `_get_host_testium_path()` returns a path to the testium package the host can read. In Flatpak the package lives under `/app/lib/testium` which the host cannot see, so the package is staged once per process under `/tmp/testium_host_*` (`/tmp` is shared) and reused. In source / wheel / PyInstaller installs under `$HOME` the original path is returned untouched.
  - `_which_host_flatpak(name)` resolves a binary by spawning `command -v` on the host (or `test -x` for absolute paths) — sandbox-visible probing under `/run/host/...` is unreliable (only `host-os` is mounted; user paths like `/scratch` aren't there).
  - `_python_version()` and `_lua_version()` go through `_run_probe()` which dispatches to `flatpak-spawn` in Flatpak so validation happens against the actual host interpreter.
  - `py_process.py` / `lua_process.py` `start()` use `flatpak_host_spawn` with `host_cwd = _get_host_testium_path()[+/lua_func]` and forward `PYTHONPATH` / `LUA_PATH` / `LUA_CPATH` / `PATH` as `--env=` arguments.
  - The `run` item's `_testium_launch_cmd()` prefixes `flatpak run org.testium.Testium` with `flatpak-spawn --host` so the sub-instance is launched by the host's `flatpak` CLI, not by an unworkable in-sandbox `flatpak` binary.
- **AppImage**: we are directly on the host filesystem, so the regular discovery on `/usr/local/bin`, `/usr/bin`, `/bin` suffices. `apply_host_libs(env)` strips `$APPDIR`-prefixed entries from `LD_LIBRARY_PATH` / `PYTHONPATH` / `PATH` and drops `PYTHONHOME` so the host Python doesn't try to load the bundled stdlib/site-packages.
- User overrides (`python_bin`/`lua_bin` in globdict): in Flatpak, both bare names and absolute paths go through `_which()` so they are validated on the host side (the sandbox can't see e.g. `/scratch/...`). Outside Flatpak, absolute paths are accepted as-is and bare names go through PATH discovery.
- If the host has no python3/lua, `ensure()` raises `ETUMRuntimeError` at test load with the candidate list — no silent fallback to a bundled interpreter.
- `py_process.py` additionally pops `PYTHONUSERBASE` (set to `/var/data/python` by the Flatpak runtime, which would hide `~/.local/lib/...`).

### Declarative test item parameters

Each `TestItem` subclass declares its accepted parameters as a class attribute `PARAMS = ParamSet(Param(...), ...)` (`interpreter/utils/param_decl.py`). The descriptor carries the parameter name, *kind* (`SCALAR` — the default and may be omitted; `LIST`; `BLOCK`; `Enum("a", "b", ...)`), `required` flag, `default`, and free-form `doc`. There is **no Python type** in the descriptor on purpose: most parameter values are expressions (`$(...)` / `<| ... |>`) whose effective type is only known after expansion, so a static type would be misleading. Post-expansion `validate=lambda v: ...` callbacks are available as an opt-in for the rare cases where a runtime check is warranted (e.g. a specific format).

`TestItem.COMMON_PARAMS` (in `test_item.py`) declares the 14 parameters accepted by every item: `name`, `doc`, `skipped`, `key`, `stop_on_failure`, `execute_on_stop`, `process_result`, `store_result`, `expected_result`, `no_fail`, `report`, `condition`, `steps`, and the internal `seq_filename` injected by the loader. The base class concatenates `COMMON_PARAMS + subclass.PARAMS` in `_validate_declared_params()` and:

- emits a `tm.print_warn(...)` listing the accepted names when an unknown key appears in the user YAML (catches typos like `param_filee`);
- raises `ETUMSyntaxError` (with the `.tum` source as context) when a `required=True` param is missing.

Validation is **opt-in per subclass**: while a subclass keeps `PARAMS = None` (the base-class default), the check is skipped entirely. This kept the migration incremental — items can be visited one by one without forcing a big-bang change. All structured items have been migrated; only the "unstructured-body" classes (`TestItemConsoleWrite`/`WriteLn` which carry the message as the raw value, `TestItemPlotActionAdd`/`Export` which take arbitrary plot-data keys, `TestItemUnittestElement` which is internally instantiated with `dict_item=None`) intentionally remain unvalidated.

Diagnostics are currently **warnings** for unknown params so an out-of-tree `.tum` with a pre-existing typo doesn't suddenly fail. The flip to a hard error is a one-line change in `_validate_declared_params()` once the user is comfortable.

Action items follow the same declarative principle. A `TestItemActions` parent (`console`, `plot`, `json_rpc`) declares its nested actions as a class attribute `ACTIONS = {yaml_key: action_class}` (e.g. `{"open": TestItemConsoleOpen, "write": …}`), mirroring `PARAMS`. The base `TestItemActions.__init__` seeds `self.action_classes` from `type(self).ACTIONS`; the imperative `register_actions(**…)` method is retained only as an escape hatch for actions that can't be known at class-definition time (none today). Because the action classes are always defined above their parent in the module, the class-level dict resolves without forward-reference gymnastics.

The schema is the realized source of truth for the LSP server (`testium lsp`), the `testium schema` CLI dump, and future auto-generated manual sections: `ParamSet.to_schema()` returns the JSON-Schema-shaped representation, and `lsp/schema.py` reads both `PARAMS` and `ACTIONS` **purely from class attributes** — no `inspect.getsource`/AST parsing. This is what lets the full schema (including nested actions) survive a frozen PyInstaller build where the `.py` source isn't on disk.

### Language server (`testium lsp`) across channels

The `testium_assist` editor extension is a thin LSP client that spawns `testium lsp` and talks JSON-RPC over stdio, so the language server must work from *every* distribution channel. Two requirements:

1. **`pygls` (+ `lsprotocol`, `cattrs`, `attrs`, `typing_extensions`) must be bundled.** It is the pyproject `[lsp]` extra (kept optional so a plain `pip install testium` stays lean), wired into each full-app channel: `build_env.sh` installs it into the shared `test/tmp/.venv` (covers **source run** and the **PyInstaller** build env); the **AppImage** installs the wheel as `…whl[lsp]`; the **Flatpak** adds a `python3-lsp` pip module (network-at-build, consistent with the manifest's global `--share=network`); the **PyInstaller** `.spec` force-collects the submodules via `collect_submodules` + explicit `hiddenimports` (including the lazily-imported `lsp`, `lsp.server`, `lsp.schema`).
2. **The schema must build without source** — handled by the declarative `PARAMS`/`ACTIONS` above; PyInstaller is the only channel that strips `.py` source, and it no longer matters.

`test/validation/lsp_check.py` enforces both per channel: `run.sh` calls it before launching the suite, asserting that `<channel> schema` returns JSON whose `console`/`plot`/`json_rpc` items still carry their actions, and that `<channel> lsp` answers an `initialize` request with capabilities (and never reports the pygls dependency missing). So `./test/validation/run.sh --mode flatpak|pyinstaller|appimage` now fails loudly if a channel ships a broken or pygls-less language server.

### Version reporting (`interpreter/utils/version.py`)

Both Flatpak and AppImage export `TESTIUM_VERSION` from a launcher (Flatpak: launcher script in `org.testium.Testium.yaml`; AppImage: `runtime.env` in `AppImageBuilder.yml`). `get_testium_version()` checks `/.flatpak-info` / `APPIMAGE` and reads `TESTIUM_VERSION` rather than relying on package metadata or repo introspection.

## Recent fixes / notable changes
- LSP across packaging channels: `testium lsp` (and the `testium_assist` editor extension that spawns it) now works from source, wheel, PyInstaller, Flatpak and AppImage. Two enablers — (1) action items declare a class-level `ACTIONS = {key: class}` registry (like `PARAMS`), so `lsp/schema.py` builds the full schema from class attributes with no `inspect.getsource`/AST (which broke under frozen PyInstaller); (2) the `[lsp]` extra (pygls) is wired into every full-app channel. `test/validation/lsp_check.py`, run by `run.sh` before the suite, asserts per-channel that `schema` keeps its actions and `lsp` answers `initialize`. See the matching architecture sections.
- Declarative test item parameters (v0.2): each `TestItem` subclass exposes a `PARAMS = ParamSet(...)` class attribute consumed by the base `__init__`. Catches unknown YAML keys (typo warnings listing the accepted names) and missing required params (load-time errors with `.tum` context). Lays the schema foundation for a future LSP server and auto-generated manual sections. See the matching architecture section.
- Flatpak: `py_func` / `lua_func` / `run` sub-instance now execute on the host via `flatpak-spawn --host`. The previous attempt to inject host lib dirs into the sandbox's `LD_LIBRARY_PATH` was abandoned — host shared libs are ABI-incompatible with the Flatpak runtime's glibc and would trip `_dl_call_libc_early_init`. The manifest gained `--talk-name=org.freedesktop.Flatpak` so the spawn proxy call is allowed. The testium package is staged once per process under `/tmp` (shared with the host) so the host interpreter can locate `py_func` / `lua_func`.
- Validation suite: single entry point with `--mode source|wheel|pyinstaller|flatpak|appimage` to validate every packaging channel against the same items. Per-mode report filenames prevent clobbering.
- Restructure: single `src/testium/` Python package (was 4 sibling top-levels: `testium`, `lib`, `py_func`, `lua_func`). `lib/` → `runtime/`, `libs/` → `api/`. `pip install` now produces a clean `site-packages/testium/` with no top-level pollution; `.lua` files travel via `package_data`.
- `bins.py`: centralised resolution + cache of external `python3` / `lua` binaries. Replaces the scattered `tm.gd("python_bin")`/`tm.gd("lua_bin")` dance and the duplicated discovery logic in `py_process.py`/`lua_process.py`. Validates at test load via `TestSet._validate_runtime_deps()` so missing interpreters fail fast.
- Subprocess API contract: user scripts in `py_func`/`lua_func` use the JSON-RPC bridge (`py_func.tm` / Lua `tm`) — never `api.testium` / `interpreter.*` directly. `SUPPORTED_API` extended with `OS`, `get_main_dir`, `init_timestamp`, `timestamp`, `timestamp_as_sec` so subprocess scripts have the same surface as main-process code.
- Report exporter plugin registry (`test_report.py`): `_EXPORTER_REGISTRY` + `entry_points("testium.exporters")` discovery. Missing format → info line, run continues.
- About dialog rework: `QVBoxLayout` (resizable), version + dirty/branch info in a `QLabel` (auto-sized), copyright + clickable EUPL-1.2 link.
- `test_ctrl.control()`: drain stale responses (left over from polled `loaded()` after `clear()` race) instead of failing on a wrong cmd key — fixes a "Unexpected return error in test set controller" seen in GUI mode after a fast reload.
- `lua_process.py`: stderr no longer DEVNULL'd so actual Lua errors (missing `cjson`/`socket`) surface instead of "Connection refused".
- `run_post_exec`: failure message uses `print_warn` (was `print_debug` — silent in non-debug runs).
- Python 3.11 compat: replaced PEP 701 nested-quote f-strings (e.g. `f"... {d["k"]} ..."`) with single-quote inner strings or string concatenation.
- `parallel` item: new item with `sync: all|any`, `wait_for`, daemon threads, `_stop_branch_recursively()`. Each branch thread registers a per-thread stdout buffer.
- `parallel_branch` icon: distinct single-arrow icon (`parallel_branch.png`).
- `parallel` F1 panel: `steps` stripped from each branch dict.
- `test_item_container.py`: shared base class extracted from Group/Cycle.
- `test_item_sleep.py`: interruptible loop so `sync: any` can stop slow branches quickly.
- `stdout_redirect.py`: `StdoutProxy` (thread-aware buffers + branch-prefixed live output, `writeln()` for Python 3.14 unittest).
- `test_report.py`: thread-safe SQLite INSERT for parallel branch concurrency.
- `terminal.py`: deleted — `-m`/`--terminal` mode removed.
- `batch.py`: premature finish bug on `gd_update` (no `"id"` key) — fix uses `"id" in m and m["id"] is None`.
- `batch.py`: `control("loaded")` deadlock on TestProcess crash — fix uses daemon thread + `threading.Event` + `is_alive()` polling.
- `termlog.py`: light/dark terminal auto-detection (`COLORFGBG`, OSC 11) + write residue bug.
- Dialog items: `auto_result`/`auto_value` for non-interactive text mode; dialogs without `auto_result` FAIL immediately in batch.
- `run` item: renamed `tum_fime` → `tum`; removed `stdout=PIPE` deadlock; PASS on any completed subprocess.
- `unittest` item: renamed from `unittest_file`.
- GUI test tree: check and fold state preserved across same-file reloads.
- Licence: EUPL-1.2.
- Interpreter override timing: `apply_overrides()` extracted from `update_global()` and called by `process.py:run()` before `eval_process_init()`, so `-d python_bin=…` / GUI prefs reach `bins.python_bin()` on its first lookup. `bins._resolve()` cache is now keyed by `(name, override)` so later `param.yaml` changes are picked up by subsequently constructed engines.

## Validation tests
Located in `test/validation/`. Two entry points:
```
./test/validation/run.sh [clean] [--mode MODE] [extra args]   # wrapper — uses a dedicated venv (see below)
./run.sh -b -- test/validation/main.tum                       # direct — testium's own python is used for test execution
```
The same item set is reused across every packaging channel — `--mode source|wheel|pyinstaller|flatpak|appimage` selects which testium binary launches the suite (`source` is the default, invoking the project's `run.sh`). Each mode stamps its results into a distinct report file (`validation-<mode>.sqlite`, `validation-<mode>-<item>.xml`) so successive runs in different modes don't clobber each other. Prerequisites (PyInstaller binary built, Flatpak bundle installed, …) are checked before launch with a hint pointing at `build_all.sh`. On Windows only `source`, `wheel`, `pyinstaller` are supported.

The `run.sh` / `run.bat` wrappers create a dedicated **host** Python venv at `${TMPDIR:-/tmp}/testium-validation-venv` (Linux) or `%TEMP%\testium-validation-venv` (Windows), with `--system-site-packages` + `pip install junit-xml`, and run the suite with `-d python_bin=…` so every test-execution subprocess (eval_proc, py_func, cycle, post_exec) runs inside that venv. testium itself keeps running in its own environment for the chosen mode. The venv is shared across modes because every test-execution subprocess ends up on the host either directly (source/wheel/pyinstaller/appimage) or via `flatpak-spawn --host` (flatpak). `clean` as the first argument recreates the venv. `wheel` mode also creates a separate `testium-wheel-venv-<v>` to hold the installed package.

The `venv` item (`test/validation/items/venv/`) asserts that the override actually took effect: `python_bin` is set, `sys.executable` matches it, `sys.prefix == dirname(dirname(python_bin))`, and `sys.prefix != sys.base_prefix` (the last marker catches the case where `python_bin` happens to be a system interpreter, which path-equality alone would miss because the venv's `bin/python3` is a symlink to the host). Both `eval_proc` (inline `<| … |>`) and `py_func` paths are exercised.

Parallel item tests: `test/validation/items/parallel/test.tum`

## Dependencies
See `src/requirements.txt`. Key ones: `pyside6`, `pyyaml`, `jinja2`, `colorama`, `gitpython`, `pexpect`, `matplotlib`.
