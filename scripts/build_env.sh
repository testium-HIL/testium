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

# Check if venv is installed
python3 -c "import venv"
if [ "$?" -ne 0 ]; then
    echo "venv must be installed on the host distribution."
    exit -1
fi
# Check if venv is installed
python3 -c "import ensurepip"
if [ "$?" -ne 0 ]; then
    echo "ensurepip must be installed on the host distribution."
    exit -1
fi

# Install the virtual environment if needed
if [ ! -d "$PY_VENV_DIR" ]; then
    echo "Creation of the virtual environment"
    python3 -m venv "$PY_VENV_DIR"
    source "$PY_VENV_DIR/bin/activate"
    pip install --extra-index-url https://pypi.python.org/pypi -r $REQ_PATH
    # Language-server deps (the pyproject [lsp] extra). Installed here so the
    # source run AND the PyInstaller build — both of which use this venv — can
    # start / collect the `testium lsp` server. pip-installed wheel users get
    # them via `pip install testium[lsp]` instead.
    pip install --extra-index-url https://pypi.python.org/pypi "pygls>=1.3"
    # Validation suite plugin used to verify the report-exporter
    # entry-points discovery end-to-end.
    FAKE_EXPORTER_DIR="$(dirname "$REQ_PATH")/../test/validation/fake_exporter"
    if [ -d "$FAKE_EXPORTER_DIR" ]; then
        pip install -e "$FAKE_EXPORTER_DIR"
    fi
fi
