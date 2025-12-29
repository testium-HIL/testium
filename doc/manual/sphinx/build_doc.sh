#! /bin/env sh

SCRIPT_DIR=$(realpath $( dirname "$0"))

ver_file="$(realpath $SCRIPT_DIR/../../../src/VERSION)"
ver=$(echo "$(cat $ver_file)" | cut -d "_" -f 1)
echo "Version of the manual: $ver"

export APP_VERSION=$ver

rm -r $SCRIPT_DIR/build
mkdir $SCRIPT_DIR/build

make -C $SCRIPT_DIR latexpdf || exit
cp -vf $SCRIPT_DIR/build/latex/testium.pdf $SCRIPT_DIR/../testium_manual.pdf
