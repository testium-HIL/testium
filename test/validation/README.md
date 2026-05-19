# Validation

This directory contains the testium validation suite. A single set of
items (`items/`), fixtures and post-processing (`post_execution.py`) is
re-used across every packaging channel.

## Running the suite

```sh
./test/validation/run.sh                       # default mode = source
./test/validation/run.sh --mode wheel
./test/validation/run.sh --mode pyinstaller
./test/validation/run.sh --mode flatpak
./test/validation/run.sh --mode appimage
```

On Windows (only `source`, `wheel`, `pyinstaller` are supported):

```bat
test\validation\run.bat --mode pyinstaller
```

Pass `clean` as the **first** argument to recreate the validation venv
from scratch (useful after a system Python upgrade):

```sh
./test/validation/run.sh clean --mode flatpak
```

Any extra arguments after the mode flag are forwarded to testium.

## Modes

| Mode          | What it launches                                            | Prerequisite                                                     |
|---------------|-------------------------------------------------------------|------------------------------------------------------------------|
| `source`      | `python3 src/testium` via the project's `run.sh`            | none — works straight out of the repo                            |
| `wheel`       | `python -m testium` inside a dedicated wheel venv           | `./build_all.sh` produced `dist/testium-<v>-py3-none-any.whl`    |
| `pyinstaller` | `dist/testium-<v>` (frozen binary)                          | `./build_all.sh` produced the PyInstaller binary                 |
| `flatpak`     | `flatpak run --command=testium org.testium.Testium`         | the Flatpak bundle is installed (`flatpak install --user dist/testium-<v>.flatpak`) |
| `appimage`    | `dist/Testium-<v>-x86_64.AppImage`                          | `./build_all.sh` produced the AppImage                           |

Each mode writes its results to a distinct report file
(`validation-<mode>.sqlite` / `validation-<mode>-<item>.xml`), so you
can run several modes in a row without clobbering previous reports.

## How `python_bin` is pinned

Every test-execution subprocess (inline `<| ... |>` evaluation,
`py_func`, `cycle`, `post_execution`, …) is routed through a dedicated
venv at `${TMPDIR:-/tmp}/testium-validation-venv`. The venv is created
with `--system-site-packages` so existing system packages stay visible,
then `junit-xml` is pip-installed for `post_execution.py`.

This is a **host** venv. In every mode (including Flatpak) the
test-execution subprocesses end up running on the host — directly for
source/wheel/pyinstaller/appimage, and via `flatpak-spawn --host` for
Flatpak — so the same venv works across modes. The wheel mode
additionally creates a separate `testium-wheel-venv-<v>` to hold the
installed wheel; that one is only used to launch testium itself.

## What is checked

The `venv` item under `items/venv/` asserts that the validation venv is
actually being used:

* `python_bin` is set in the global dict.
* The eval subprocess (used for `<| ... |>` expressions) has
  `sys.executable == python_bin`, `sys.prefix == dirname(dirname(python_bin))`,
  and `sys.prefix != sys.base_prefix` (i.e. is actually inside a venv).
* A `py_func` subprocess passes the same three checks.

These checks use `abspath`/`normpath` rather than `realpath` on
purpose: the venv's `bin/python3` is a symlink to the host interpreter,
so `realpath` would map both venv and non-venv interpreters to the same
target. `sys.prefix != sys.base_prefix` is the venv-specific marker
that distinguishes the two cases.
