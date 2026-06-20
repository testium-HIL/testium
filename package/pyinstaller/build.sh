#! /bin/env sh

SCRIPT_DIR=$(realpath $( dirname "$0"))

rm -rf "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist"

pwd=$(pwd)
cd ${SCRIPT_DIR}
# PYI_WORKPATH (set by build_all --ram) puts the big intermediate build tree on
# tmpfs; dist/ stays local so build_all can collect the binary.
WORKARG=""
[ -n "$PYI_WORKPATH" ] && WORKARG="--workpath $PYI_WORKPATH"
pyinstaller $WORKARG testium.spec
RESULT=$?
if [ -n "$1" ] && [ "$1" = "install" ]; then
    if [ $RESULT -eq 0 ]; then
        install -v "dist/testium" "${HOME}/.local/bin/"
    fi
fi
cd $pwd
