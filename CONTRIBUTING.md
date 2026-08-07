# Contributing to testium

Thank you for your interest in contributing to testium.

## License of contributions

testium is licensed under the **European Union Public Licence v. 1.2 (EUPL-1.2)** —
see the [LICENSE](LICENSE) file at the repository root.

By submitting a contribution to this project (pull request, patch, issue
attachment, or any other form of code, documentation or media), you agree
that your contribution is licensed to the project and to the public under the
**same EUPL-1.2** terms (or any later version of the EUPL approved by the
European Commission), and you certify that:

- you are the author of the contribution, or you have the right to submit it
  under the EUPL-1.2;
- to the best of your knowledge, the contribution does not infringe any
  third-party intellectual-property rights;
- the contribution may be redistributed by the project under the EUPL-1.2 and
  any compatible licence listed in the EUPL-1.2 Appendix.

This is the **inbound = outbound** rule: contributions come in under the same
licence the project ships under.

You retain copyright on your contribution. The project does **not** ask you
to sign a CLA or assign your copyright.

## SPDX header in new source files

When creating a new source file, please include the following header at the
top of the file (adjust the comment marker to the file's language):

```python
# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) <year> <your name>
```

For existing files, keep the header that is already there.

## How to contribute

1. Open an issue describing the change you want to make (bug, feature, doc).
2. Fork <https://github.com/testium-HIL/testium>, create a topic branch.
3. Commit with a clear message (one logical change per commit).
4. Make sure the validation suite still passes:
   ```
   ./test/validation/run.sh
   ```
5. Open a pull request against `main`.

## Code organization

`src/testium/` is split along the **process boundary**, not by theme:

| Package | Runs in | Role |
|---|---|---|
| `interpreter/` | main process | test engine (load, items, reports) |
| `main_win/` | main process | PySide6 GUI |
| `api/` | main process | runtime API implementation; subprocesses reach it only through the JSON-RPC bridge |
| `lsp/` | main process | `testium lsp` / `testium schema` |
| `runtime/` | **both sides** | shared floor: RPC link, exceptions, report helper, export worker — loaded by the main process *and* by the host-Python subprocesses |
| `py_func/`, `lua_func/` | host interpreter | subprocess-side bridges |

Rules:

- `py_func/` and `lua_func/` import only `runtime/` and themselves — never
  `interpreter`, `main_win` or `api`. Enforced by
  `test/validation/items/isolation/`.
- `runtime/` stays standard-library only: the host interpreter does not
  have testium's dependencies.
- Repo roots: code in `src/`, tests and fixtures in `test/`, documentation
  in `doc/`, per-channel packaging in `package/`. `schema/tum.json` is the
  only tracked generated artifact (public schema reference, see
  `schema/README.md`).

## Coding conventions

- Python ≥ 3.11
- Follow existing style in the file you are modifying
- Add or update tests in `test/validation/` for new test items or behaviours
- Update `CLAUDE.md` and the Sphinx manual for user-visible changes

### Comments

Comments must be short and factual. State what the code does or why a
non-obvious choice was made, in as few lines as possible.

- No essays: if a comment needs more than two or three lines, the code or
  the commit message is the right place.
- No restating the code, no narrating the history of a fix.
- No humour, no slang, no jargon of the "funcky", "smoke test", "flaky",
  "magic", "hack" kind. Plain, neutral wording only.

## Development

### Developer debugging

Two switches help debugging testium itself. They are development tools:
they are not part of the user documentation.

- `-g` / `--dev-debug` — imports `debugpy` in the GUI status thread so a
  Python debugger can attach to the running testium.
- `debug_rpc` — traces the JSON-RPC frames exchanged with the py_func /
  lua_func subprocesses. It requires the user debug output too, and is
  read when an engine starts, so set both before loading:

  ```sh
  testium -d test_debug -d debug_rpc mytest.tum
  ```

  The eval engine starts at load time; py_func / lua_func engines start
  per item (or once per `context_id`).

### Debugging in VSCode

The recommended workflow:

1. Add a debug configuration to `.vscode/launch.json`:
   ```json
   {
       "configurations": [
           {
               "name": "Python : testium",
               "type": "python",
               "request": "launch",
               "program": "${workspaceFolder}/src/testium",
               "console": "integratedTerminal",
               "args": ["-g"],
               "justMyCode": true
           }
       ]
   }
   ```
2. Install `debugpy` in the venv: `python -m pip install debugpy`.
3. Open the *Run and Debug* tab and press play. testium starts; load and
   run a `.tum` file. Set breakpoints where you want to investigate.

### Qt GUI modification

UI files (`*.ui`) are edited in **Qt Creator**. After editing, regenerate
the corresponding Python and resource files:

```sh
scripts/qt_generate.sh
```

Icons come from <https://github.com/free-icons/free-icons>.

The README session capture `doc/testium_session.gif` is regenerated with:

```sh
test/tmp/.venv/bin/python3 scripts/make_session_gif.py
```

### Sphinx documentation

```sh
pip install sphinx linuxdoc
doc/manual/sphinx/build_doc.sh
```

PDF generation requires `texlive`:

```sh
sudo apt install texlive-full
```

### Validation suite

The single entry point is `test/validation/run.sh` (`run.ps1` on Windows).
It prepares a dedicated venv under `/tmp/testium-validation-venv`
(junit-xml, pytest, jsonschema, pyyaml), runs the pre-checks — language
server (`lsp_check.py`), JSON Schema dump (`schema_check.py`), load-error
messages (`load_errors_check.py`), GUI reload leaks (`gui_reload_check.py`,
source mode only) — then executes the full suite headless. Pass `--gui` to
run it through the GUI instead (`-r`: opens, runs, closes).

```sh
./test/validation/run.sh
```

The same suite validates every packaging channel via `--mode`
(`source` is the default; the others need the artifact built or installed
first, see `test/validation/README.md`):

```sh
./test/validation/run.sh --mode source|wheel|pyinstaller|flatpak|appimage
```

Useful variants:

```sh
./test/validation/run.sh clean            # recreate the venv first (after a Python upgrade)
./test/validation/run.sh --gui            # load the suite in the GUI, run it manually
./test/validation/run.sh -d "items=['parallel','common']"   # subset run
```

Extra arguments are forwarded to testium. The report file is suffixed
with the mode (`validation-source.sqlite`, ...) so runs in different
modes don't overwrite each other.

### Cross-distribution check

`package/deb/test_distro.sh` spins up a Docker/Podman container of the
target image, installs the expected system Python deps via apt (with
pip fallback for what is missing), installs the testium wheel and runs
the validation suite end-to-end. Currently green on `debian:bookworm`,
`debian:trixie`, `ubuntu:24.04`.

```sh
./package/deb/test_distro.sh debian:trixie
```

## Release procedure

1. Update `release_note.txt` (one short user-facing bullet per change).
2. Bump the version in `src/VERSION`.
3. Build every artifact into `dist/`:
   ```sh
   ./build_all.sh          # manual PDF, wheel, PyInstaller binary, Flatpak, AppImage
   ```
   On Windows: `build_all.ps1` (wheel + onedir exe + installer).
   `build_all.sh` skips a step whose artifact already exists; pass `--clean`
   to rebuild everything (it also copies `release_note.txt` to `dist/` and
   warns if it has no entry for the version being built).
4. Validate each channel with the suite:
   ```sh
   ./test/validation/run.sh --mode wheel
   ./test/validation/run.sh --mode pyinstaller
   flatpak install --user dist/testium-<v>.flatpak && ./test/validation/run.sh --mode flatpak
   ./test/validation/run.sh --mode appimage
   ```
5. Confirm all validation results are green before publishing.
6. Push and tag the commit with the new version.

## Reporting security issues

Please do **not** report security vulnerabilities through public GitHub
issues. Instead, send an email to the project maintainer directly.

## Questions

Open a GitHub Discussion or an issue tagged `question`.
