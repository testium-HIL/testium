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

# Install the virtual environment if needed
if [ ! -d "$PY_VENV_DIR" ]; then
    echo "Creation of the virtual environment"
    python3 -m venv "$PY_VENV_DIR"
    source "$PY_VENV_DIR/bin/activate"
    pip install --extra-index-url https://pypi.python.org/pypi -r $REQ_PATH
fi
