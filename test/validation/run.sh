#!/bin/bash
# Runs the testium validation suite with a dedicated Python venv used by
# every py_func / cycle / inline-eval subprocess (i.e. everything that
# goes through ``bins.python_bin()``). testium itself keeps running in
# the project's own environment — the validation venv only isolates
# *test execution*.
#
#   ./test/validation/run.sh [clean] [extra testium args]
#
# ``clean`` (optional, must be the first arg) removes the venv before
# recreating it; this is the way to refresh the venv after a system
# Python upgrade.

set -e

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(realpath "$(dirname "$SCRIPT_PATH")")"
PROJECT_DIR="$(realpath "$SCRIPT_DIR/../..")"
# Venv lives in the system temp dir so it stays out of the project tree
# (and is naturally cleaned up by tmpfiles/reboot on most distros).
VENV_DIR="${TMPDIR:-/tmp}/testium-validation-venv"

if [ "${1:-}" = "clean" ]; then
    rm -rf "$VENV_DIR"
    shift
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating validation venv at $VENV_DIR"
    # --system-site-packages so we don't have to reinstall pyside6, lxml
    # & friends just to support the validation helpers. We still pip
    # install junit-xml below because it is the one dep that does *not*
    # ship as a system package on most distros and is required by
    # post_execution.py.
    python3 -m venv --system-site-packages "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet junit-xml
fi

VENV_PYTHON="$VENV_DIR/bin/python3"

# Delegate to the project's run.sh so testium itself still runs in the
# project venv (with pyside6, gitpython, ...). ``-d python_bin=...``
# pins every test-execution subprocess to the validation venv.
exec "$PROJECT_DIR/run.sh" -b \
    -d "python_bin=$VENV_PYTHON" \
    -- "$SCRIPT_DIR/main.tum" "$@"
