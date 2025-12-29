#! /bin/env sh

SCRIPT_DIR=$(realpath $( dirname "$0"))

rm -r "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist"

pwd=$(pwd)
cd ${SCRIPT_DIR}
pyinstaller testium.spec
RESULT=$?
if [ -n "$1" ] && [ "$1" = "install" ]; then
    if [ $RESULT -eq 0 ]; then
        install -v "dist/testium" "${HOME}/.local/bin/"
    fi
fi
cd $pwd
