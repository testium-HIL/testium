#!/bin/bash
# Build every distribution channel of testium, in order:
#   1. Manual PDF         -> dist/testium-manual-<v>.pdf
#   2. Wheel              -> dist/testium-<v>-py3-none-any.whl   (PEP 427 name)
#   3. PyInstaller binary -> dist/testium-<v>
#   4. Flatpak bundle     -> dist/testium-<v>.flatpak
#   5. AppImage           -> dist/Testium-<v>-x86_64.AppImage    (original name)
# release_note.txt is copied to dist/ up front (with a warning if it has no
# entry for the current version).
#
# By default, a step is skipped if its artifact already exists in dist/.
# Pass --clean to remove existing dist/ artifacts and rebuild everything.
#
# All artifacts are collected (copied) under <repo>/dist/. Original outputs in
# src/dist/, package/*/dist/, doc/manual/ are left in place. Wheel and AppImage
# keep their original names (which already contain the version); manual,
# pyinstaller and flatpak are renamed to testium(-manual)-<version>(.suff).
#
# Re-uses scripts/build_env.sh and scripts/set_env.sh — the same pair invoked
# by run.sh — so the venv at test/tmp/.venv stays the single source of Python
# dependencies. `build`, `pyinstaller`, `sphinx` and `linuxdoc` are installed
# into that venv on demand if not already there. Flatpak and AppImage build in
# their own container/sandbox; their build.sh scripts have their own toolchain
# checks.

set -e

CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --clean|-c) CLEAN=1 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

SCRIPT_DIR=$(realpath "$(dirname "$0")")
VERSION=$(cat "$SCRIPT_DIR/src/VERSION")
DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"

if [ "$CLEAN" -eq 1 ]; then
    echo "-- clean: removing existing dist artifacts for version $VERSION"
    rm -f "$DIST_DIR/testium-manual-${VERSION}.pdf"
    rm -f "$DIST_DIR"/testium-${VERSION}-*.whl
    rm -f "$DIST_DIR/testium-${VERSION}"
    rm -f "$DIST_DIR/testium-${VERSION}.flatpak"
    rm -f "$DIST_DIR"/Testium-${VERSION}-*.AppImage
fi

# Release note: copy it to dist/ and warn (but don't fail) if it has no entry
# for the current version.
RELEASE_NOTE_SRC="$SCRIPT_DIR/release_note.txt"
RELEASE_NOTE="$DIST_DIR/release_note.txt"
cp -f "$RELEASE_NOTE_SRC" "$RELEASE_NOTE"
if ! grep -qE "^version $VERSION([^.0-9]|$)" "$RELEASE_NOTE_SRC"; then
    echo "WARNING: release_note.txt has no entry for version $VERSION." >&2
fi

export PY_VENV_NAME=".venv"
export PY_VENV_DIR="$SCRIPT_DIR/test/tmp/$PY_VENV_NAME"
export REQ_PATH="$SCRIPT_DIR/src/requirements.txt"

bash "$SCRIPT_DIR/scripts/build_env.sh"
source "$SCRIPT_DIR/scripts/set_env.sh"

step() {
    echo
    echo "================================================================"
    echo "  $1"
    echo "================================================================"
}

skip() { echo "  (already built — skipping)"; }

# 1. Manual PDF
MANUAL="$DIST_DIR/testium-manual-${VERSION}.pdf"
step "1/5  Manual PDF (version $VERSION)"
if [ ! -f "$MANUAL" ]; then
    python -m pip install --quiet --upgrade sphinx linuxdoc
    bash "$SCRIPT_DIR/doc/manual/sphinx/build_doc.sh"
    cp -f "$SCRIPT_DIR/doc/manual/testium_manual.pdf" "$MANUAL"
else
    skip
fi

# 2. Wheel — PEP 427 name kept (already contains version)
step "2/5  Wheel (version $VERSION)"
WHEEL=$(ls -1t "$DIST_DIR"/testium-${VERSION}-*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
    python -m pip install --quiet --upgrade build
    (
        cd "$SCRIPT_DIR/src"
        rm -rf dist build *.egg-info
        python -m build --wheel
    )
    WHEEL_SRC=$(ls -1t "$SCRIPT_DIR/src/dist"/*.whl | head -1)
    WHEEL="$DIST_DIR/$(basename "$WHEEL_SRC")"
    cp -f "$WHEEL_SRC" "$WHEEL"
else
    skip
fi

# 3. PyInstaller binary
PYI_BIN="$DIST_DIR/testium-${VERSION}"
step "3/5  PyInstaller binary (version $VERSION)"
if [ ! -f "$PYI_BIN" ]; then
    python -m pip install --quiet --upgrade pyinstaller
    bash "$SCRIPT_DIR/package/pyinstaller/build.sh"
    cp -f "$SCRIPT_DIR/package/pyinstaller/dist/testium" "$PYI_BIN"
else
    skip
fi

# 4. Flatpak bundle
FLATPAK_BUNDLE="$DIST_DIR/testium-${VERSION}.flatpak"
step "4/5  Flatpak bundle (version $VERSION)"
if [ ! -f "$FLATPAK_BUNDLE" ]; then
    FLATPAK_DEPS=(
        "org.kde.Platform//6.10"
        "org.kde.Sdk//6.10"
        "io.qt.PySide.BaseApp//6.10"
    )
    if ! flatpak remotes --user | grep -q "^flathub"; then
        echo "  Adding Flathub remote"
        flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    fi
    for dep in "${FLATPAK_DEPS[@]}"; do
        if ! flatpak info --user "$dep" &>/dev/null && ! flatpak info --system "$dep" &>/dev/null; then
            echo "  Installing Flatpak dependency: $dep"
            flatpak install --user --noninteractive flathub "$dep"
        fi
    done
    (
        cd "$SCRIPT_DIR/package/flatpak"
        bash build.sh
    )
    cp -f "$SCRIPT_DIR/package/flatpak/testium.flatpak" "$FLATPAK_BUNDLE"
else
    skip
fi

# 5. AppImage
step "5/5  AppImage (version $VERSION)"
APPIMAGE=$(ls -1t "$DIST_DIR"/Testium-${VERSION}-*.AppImage 2>/dev/null | head -1)
if [ -z "$APPIMAGE" ]; then
    (
        cd "$SCRIPT_DIR/package/appimage"
        bash build.sh
    )
    APPIMAGE_SRC=$(ls -1t "$SCRIPT_DIR/package/appimage"/*.AppImage 2>/dev/null | head -1)
    APPIMAGE="$DIST_DIR/$(basename "$APPIMAGE_SRC")"
    cp -f "$APPIMAGE_SRC" "$APPIMAGE"
    chmod +x "$APPIMAGE"
else
    skip
fi

step "All packages built"
printf "  manual       : %s\n" "$MANUAL"
printf "  wheel        : %s\n" "$WHEEL"
printf "  pyinstaller  : %s\n" "$PYI_BIN"
printf "  flatpak      : %s\n" "$FLATPAK_BUNDLE"
printf "  appimage     : %s\n" "$APPIMAGE"
printf "  release_note : %s\n" "$RELEASE_NOTE"
