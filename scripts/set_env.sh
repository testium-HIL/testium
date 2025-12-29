#!/bin/bash

if [ -z $PY_VENV_DIR ]; then
    echo "PY_VENV_NAME must be defined"
    exit -1
fi

source "$PY_VENV_DIR/bin/activate"
