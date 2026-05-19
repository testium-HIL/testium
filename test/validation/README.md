# Validation

This directory contains the testium validation suite.

## Running the suite

```sh
./test/validation/run.sh           # Linux
test\validation\run.bat            # Windows
```

The wrapper creates a dedicated Python venv in the system temp dir
(`${TMPDIR:-/tmp}/testium-validation-venv` on Linux, `%TEMP%\testium-validation-venv`
on Windows), using `--system-site-packages` so existing system packages
stay visible. The validation suite is then run with that venv pinned as
`python_bin`. Every test-execution subprocess (inline `<| ... |>`
evaluation, `py_func`, `cycle`, `post_execution`, ...) runs inside the
venv, while testium itself keeps running in the project's own
environment.

Pass `clean` as the first argument to recreate the venv from scratch
(useful after a system Python upgrade):

```sh
./test/validation/run.sh clean
```

## What is checked

The `venv` item under `items/venv/` asserts that the venv is actually
being used:

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
