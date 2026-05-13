#!/bin/bash
# Build every distribution channel of testium, in order:
#   1. Wheel              -> dist/testium-<v>-py3-none-any.whl   (PEP 427 name)
#   2. PyInstaller binary -> dist/testium-<v>
#   3. Flatpak bundle     -> dist/testium-<v>.flatpak
#   4. AppImage           -> dist/Testium-<v>-x86_64.AppImage    (original name)
# All artifacts are collected (copied) under <repo>/dist/. Original outputs in
# src/dist/, package/*/dist/ are left in place. The wheel and AppImage keep
# their original names (which already contain the version); pyinstaller and
# flatpak are renamed to a normalized testium-<version>(.suff) form.
#
# Re-uses scripts/build_env.sh and scripts/set_env.sh — the same pair invoked
# by run.sh — so the venv at test/tmp/.venv stays the single source of Python
# dependencies. `build` and `pyinstaller` are installed into that venv on
# demand if not already there. Flatpak and AppImage build in their own
# container/sandbox; their build.sh scripts have their own toolchain checks.

set -e

SCRIPT_DIR=$(realpath "$(dirname "$0")")
VERSION=$(cat "$SCRIPT_DIR/src/VERSION")
DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"

export PY_VENV_NAME=".venv"
export PY_VENV_DIR="$SCRIPT_DIR/test/tmp/$PY_VENV_NAME"
export REQ_PATH="$SCRIPT_DIR/src/requirements.txt"

bash "$SCRIPT_DIR/scripts/build_env.sh"
source "$SCRIPT_DIR/scripts/set_env.sh"

# Ensure wheel/PyInstaller toolchains are present in the venv.
python -m pip install --quiet --upgrade build pyinstaller

step() {
    echo
    echo "================================================================"
    echo "  $1"
    echo "================================================================"
}

# 1. Wheel — PEP 427 name kept (already contains version)
step "1/4  Wheel (version $VERSION)"
(
    cd "$SCRIPT_DIR/src"
    rm -rf dist build *.egg-info
    python -m build --wheel
)
WHEEL_SRC=$(ls -1t "$SCRIPT_DIR/src/dist"/*.whl | head -1)
WHEEL="$DIST_DIR/$(basename "$WHEEL_SRC")"
cp -f "$WHEEL_SRC" "$WHEEL"

# 2. PyInstaller binary
step "2/4  PyInstaller binary (version $VERSION)"
bash "$SCRIPT_DIR/package/pyinstaller/build.sh"
PYI_SRC="$SCRIPT_DIR/package/pyinstaller/dist/testium"
PYI_BIN="$DIST_DIR/testium-${VERSION}"
cp -f "$PYI_SRC" "$PYI_BIN"

# 3. Flatpak bundle
step "3/4  Flatpak bundle (version $VERSION)"
(
    cd "$SCRIPT_DIR/package/flatpak"
    bash build.sh
)
FLATPAK_SRC="$SCRIPT_DIR/package/flatpak/testium.flatpak"
FLATPAK_BUNDLE="$DIST_DIR/testium-${VERSION}.flatpak"
cp -f "$FLATPAK_SRC" "$FLATPAK_BUNDLE"

# 4. AppImage
step "4/4  AppImage (version $VERSION)"
(
    cd "$SCRIPT_DIR/package/appimage"
    bash build.sh
)
APPIMAGE_SRC=$(ls -1t "$SCRIPT_DIR/package/appimage"/*.AppImage 2>/dev/null | head -1)
APPIMAGE="$DIST_DIR/$(basename "$APPIMAGE_SRC")"
cp -f "$APPIMAGE_SRC" "$APPIMAGE"
chmod +x "$APPIMAGE"

step "All packages built"
printf "  wheel       : %s\n" "$WHEEL"
printf "  pyinstaller : %s\n" "$PYI_BIN"
printf "  flatpak     : %s\n" "$FLATPAK_BUNDLE"
printf "  appimage    : %s\n" "$APPIMAGE"
