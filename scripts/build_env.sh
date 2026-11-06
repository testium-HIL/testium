#!/bin/bash

if [ -z $PY_VENV_DIR ]; then
    echo "PY_VENV_DIR must be defined"
    exit -1
fi

if [ -z $REQ_PATH ]; then
    echo "REQ_PATH must be defined"
    exit -1
fi

if [ "$1" == "clean" ]; then
    rm -Rf "$PY_VENV_DIR"
fi

# venv support (module + ensurepip, needed to bootstrap pip) must be present.
if ! python3 -c "import venv, ensurepip" 2>/dev/null; then
    echo "venv support is missing on this system. On Debian/Ubuntu: sudo apt install python3-venv"
    exit 1
fi

# Install the virtual environment if needed
if [ ! -d "$PY_VENV_DIR" ]; then
    echo "Creation of the virtual environment"
    python3 -m venv "$PY_VENV_DIR"
fi

# (Re)install whenever the pinned set differs from the last one installed,
# so a regenerated requirements.txt reaches an existing venv.
STAMP="$PY_VENV_DIR/requirements.installed"
if ! cmp -s "$REQ_PATH" "$STAMP"; then
    echo "Installing the pinned dependencies ($REQ_PATH)"
    "$PY_VENV_DIR/bin/python" -m pip install --extra-index-url https://pypi.python.org/pypi -r "$REQ_PATH"
    cp "$REQ_PATH" "$STAMP"
fi
