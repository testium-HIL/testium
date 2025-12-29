#!/bin/bash

#set -x

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR=$(realpath $( dirname "$SCRIPT_PATH"))

export PY_VENV_NAME=".venv"
export PY_VENV_DIR="$SCRIPT_DIR/test/tmp/$PY_VENV_NAME"
export REQ_PATH="$SCRIPT_DIR/src/requirements.txt"

bash $SCRIPT_DIR/scripts/build_env.sh
source $SCRIPT_DIR/scripts/set_env.sh

python3 "$SCRIPT_DIR/src/testium"  $@
