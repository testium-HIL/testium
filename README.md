# testium

testium is a YAML-driven test sequencer for hardware-in-the-loop and
integration testing. A test campaign is described in a `.tum` file as a tree
of items (checks, console interactions, Python/Lua functions, parallel blocks,
dialogs, …); testium executes the tree, captures results, and produces
reports in several formats.

## Documentation

* [Quick start](doc/quick_start.md) — install and run your first test in
  five minutes.
* [Tutorial](doc/tutorial.md) — guided walk-through of the most common
  test items with a runnable example.
* [User manual (PDF)](doc/manual/testium_manual.pdf) — full reference.
* [`doc/examples/`](doc/examples/) — runnable `.tum` snippets.

## Pre-built releases

Pre-built artifacts are published at
<https://git.beafrancois.fr/v-and-v/testium/releases>:

* **Python wheel** (`testium-<version>-py3-none-any.whl`) — install with
  `pip install testium-*.whl`. Lighter than the binary; pulls Python
  dependencies from PyPI on install.
* **Self-contained Linux binary** (`testium`, built with PyInstaller) —
  runnable directly, no Python installation required on the host. Lua
  support still needs a system `lua` interpreter and the `lua-socket` /
  `lua-cjson` modules.
* **Flatpak** — *coming soon.*

## Quick start

From a checkout of the repository:

| OS | Command |
|----|---------|
| Linux | `./run.sh` |
| Windows (cmd) | `run.bat` |
| Windows (PowerShell) | `run.ps1` |

The wrapper creates a Python virtual environment on first run and starts
testium in GUI mode. Add `-b path/to/test.tum` to run a test in batch mode.

## Manual installation

If the wrapper script does not fit your environment, set up testium manually:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
```

Required Python packages (see `src/requirements.txt`):
`pyside6`, `pyserial`, `pyyaml`, `pexpect`, `gitpython`, `jinja2`, `colorama`,
`matplotlib`, `junit-xml`, `lxml`.

For tests using `lua_func` items, install Lua (>= 5.1) plus the `socket` and
`cjson` modules. On Debian/Ubuntu:

```sh
sudo apt install lua5.4 lua-socket lua-cjson
```

Run testium:

```sh
python3 src/testium               # GUI
python3 src/testium -b mytest.tum # batch
```

## Troubleshooting

### `wl_proxy_marshal_flags` symbol error

```
testium: symbol lookup error: ... undefined symbol: wl_proxy_marshal_flags
```

Force the X11 Qt backend:

```sh
export QT_QPA_PLATFORM=xcb
testium
```

### `xcb plugin missing`

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
```

Install the missing system libraries:

```sh
sudo apt install libxcb-cursor0 libicu-dev libxcb-cursor-dev
```

## License

Copyright © 2025-2026 François Dausseur.

testium is distributed under the **European Union Public Licence v. 1.2
(EUPL-1.2)** — see [`LICENSE`](LICENSE) for the full text. SPDX:
`EUPL-1.2`.

Contributions are accepted under the same licence (inbound = outbound).
See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, debugging
workflow, and the release procedure.
