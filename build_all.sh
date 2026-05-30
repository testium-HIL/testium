#!/bin/bash
# Build every distribution channel of testium:
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
# Parallelism: the wheel is built first (the AppImage installs it), then the
# manual, PyInstaller, Flatpak and AppImage builds run concurrently. The shared
# venv at test/tmp/.venv is only WRITTEN during the serial prep phase (the
# `pip install` of build/sphinx/pyinstaller); the parallel builds only read it,
# so there is no concurrent-pip race. Pass --serial to build one step at a time
# (useful when debugging or on a resource-constrained machine). Per-step output
# of the parallel phase is captured under dist/.build-logs/<step>.log and the
# log of any failing step is printed at the end.
#
# Pass --ram to redirect the per-channel build scratch (PyInstaller workpath,
# Flatpak build dir + ostree repo, AppImage AppDir) and TMPDIR/PIP_CACHE_DIR to
# /dev/shm, and skip UPX. Big speedup on slow/flash storage. On a RAM-limited
# machine combine with --serial (e.g. ./build_all.sh --ram --serial).
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
SERIAL=0
RAM=0
for arg in "$@"; do
    case "$arg" in
        --clean|-c) CLEAN=1 ;;
        --serial)   SERIAL=1 ;;
        --ram)      RAM=1 ;;
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

# ---------- RAM mode: put build scratch on tmpfs (--ram) ----------------------
# On slow storage (USB stick, SD card) the per-channel build dirs and temp
# churn dominate. --ram redirects them to /dev/shm and skips UPX. The whole
# Flatpak working set (build dir + .flatpak-builder + repo) goes to tmpfs
# because flatpak-builder requires its state dir on the same filesystem as the
# build dir — so its download cache doesn't persist across --ram runs. The
# tmpfs scratch is freed on exit.
if [ "$RAM" -eq 1 ]; then
    RAMROOT="/dev/shm/testium-build-${VERSION}"
    echo "-- RAM mode: build scratch under $RAMROOT (tmpfs), freed on exit"
    rm -rf "$RAMROOT"
    mkdir -p "$RAMROOT"/{tmp,pip,pyi-work,flatpak-build,flatpak-state,flatpak-repo,appdir}
    export TMPDIR="$RAMROOT/tmp"
    export PIP_CACHE_DIR="$RAMROOT/pip"
    export PYI_WORKPATH="$RAMROOT/pyi-work"            # pyinstaller --workpath
    export FLATPAK_BUILDDIR="$RAMROOT/flatpak-build"   # flatpak-builder build dir
    export FLATPAK_STATEDIR="$RAMROOT/flatpak-state"   # .flatpak-builder (same fs as build dir, required)
    export FLATPAK_REPODIR="$RAMROOT/flatpak-repo"     # ostree repo
    export APPIMAGE_APPDIR_TMPFS="$RAMROOT/appdir"    # AppDir bind-mount
    export TESTIUM_NO_UPX=1                           # skip slow UPX in the spec
    trap 'rm -rf "$RAMROOT"' EXIT
    if [ "$SERIAL" -ne 1 ]; then
        echo "   note: with --ram, prefer adding --serial so each step gets the"
        echo "         full tmpfs and you don't risk OOM (flatpak+appimage are ~1 GB each)."
    fi
fi

step() {
    echo
    echo "================================================================"
    echo "  $1"
    echo "================================================================"
}

# Kill a process and its whole descendant tree (children first) — used by the
# interrupt handler so SIGINT also stops grandchildren the parallel jobs spawned
# (podman container, flatpak-builder, pyinstaller …), not just the subshells.
_kill_tree() {
    local pid=$1 c
    for c in $(pgrep -P "$pid" 2>/dev/null); do
        _kill_tree "$c"
    done
    kill -TERM "$pid" 2>/dev/null || true
}

# Set as INT/TERM handler around the parallel wait. Stops every running build
# tree, then exits — the EXIT trap (set under --ram) frees the tmpfs scratch.
_interrupt() {
    echo >&2
    echo "-- interrupted: stopping running builds…" >&2
    local pid
    for pid in "${!PID2NAME[@]}"; do
        _kill_tree "$pid"
    done
    exit 130
}

# ---------- artifact paths ----------------------------------------------------

MANUAL="$DIST_DIR/testium-manual-${VERSION}.pdf"
PYI_BIN="$DIST_DIR/testium-${VERSION}"
FLATPAK_BUNDLE="$DIST_DIR/testium-${VERSION}.flatpak"
wheel_in_dist() { ls -1t "$DIST_DIR"/testium-${VERSION}-*.whl 2>/dev/null | head -1; }
appimage_in_dist() { ls -1t "$DIST_DIR"/Testium-${VERSION}-*.AppImage 2>/dev/null | head -1; }

# ---------- per-step build functions (assume tools are installed) -------------

build_wheel() {
    if [ -n "$(wheel_in_dist)" ]; then echo "wheel: already built — skipping"; return 0; fi
    echo "wheel: building"
    (
        cd "$SCRIPT_DIR/src"
        rm -rf dist build *.egg-info
        python -m build --wheel
    )
    local src; src=$(ls -1t "$SCRIPT_DIR/src/dist"/*.whl | head -1)
    cp -f "$src" "$DIST_DIR/$(basename "$src")"
    echo "wheel: done"
}

build_manual() {
    if [ -f "$MANUAL" ]; then echo "manual: already built — skipping"; return 0; fi
    echo "manual: building"
    bash "$SCRIPT_DIR/doc/manual/sphinx/build_doc.sh"
    cp -f "$SCRIPT_DIR/doc/manual/testium_manual.pdf" "$MANUAL"
    echo "manual: done"
}

build_pyinstaller() {
    if [ -f "$PYI_BIN" ]; then echo "pyinstaller: already built — skipping"; return 0; fi
    echo "pyinstaller: building"
    bash "$SCRIPT_DIR/package/pyinstaller/build.sh"
    cp -f "$SCRIPT_DIR/package/pyinstaller/dist/testium" "$PYI_BIN"
    echo "pyinstaller: done"
}

build_flatpak() {
    if [ -f "$FLATPAK_BUNDLE" ]; then echo "flatpak: already built — skipping"; return 0; fi
    echo "flatpak: building"
    (
        cd "$SCRIPT_DIR/package/flatpak"
        bash build.sh
    )
    cp -f "$SCRIPT_DIR/package/flatpak/testium.flatpak" "$FLATPAK_BUNDLE"
    echo "flatpak: done"
}

build_appimage() {
    if [ -n "$(appimage_in_dist)" ]; then echo "appimage: already built — skipping"; return 0; fi
    echo "appimage: building"
    (
        cd "$SCRIPT_DIR/package/appimage"
        bash build.sh
    )
    local src; src=$(ls -1t "$SCRIPT_DIR/package/appimage"/*.AppImage 2>/dev/null | head -1)
    cp -f "$src" "$DIST_DIR/$(basename "$src")"
    chmod +x "$DIST_DIR/$(basename "$src")"
    echo "appimage: done"
}

# ---------- serial prep: tool installs (shared venv) + flatpak runtimes -------

step "Prep: build tools + runtimes (serial — shared venv)"

[ -f "$MANUAL" ]   || python -m pip install --quiet --upgrade sphinx linuxdoc
[ -n "$(wheel_in_dist)" ] || python -m pip install --quiet --upgrade build
[ -f "$PYI_BIN" ]  || python -m pip install --quiet --upgrade pyinstaller

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
fi

# ---------- serial: wheel (the AppImage installs it) --------------------------

step "1/5  Wheel (version $VERSION)"
build_wheel

# ---------- build the rest --------------------------------------------------

REST=(manual pyinstaller flatpak appimage)

if [ "$SERIAL" -eq 1 ]; then
    n=2
    for name in "${REST[@]}"; do
        step "$n/5  $name (version $VERSION)"
        "build_$name"
        n=$((n + 1))
    done
else
    step "2-5/5  manual + pyinstaller + flatpak + appimage (parallel)"
    LOGDIR="$DIST_DIR/.build-logs"
    mkdir -p "$LOGDIR"
    declare -A PID2NAME
    for name in "${REST[@]}"; do
        log="$LOGDIR/$name.log"
        echo "  -> launching $name (log: $log)"
        ( "build_$name" ) >"$log" 2>&1 &
        PID2NAME[$!]="$name"
    done

    # From here until all jobs are reaped, Ctrl+C stops every build tree.
    trap _interrupt INT TERM

    FAILED=()
    for pid in "${!PID2NAME[@]}"; do
        name="${PID2NAME[$pid]}"
        if wait "$pid"; then
            echo "  -> $name: OK"
        else
            echo "  -> $name: FAILED (rc=$?)"
            FAILED+=("$name")
        fi
    done

    trap - INT TERM

    if [ "${#FAILED[@]}" -gt 0 ]; then
        for name in "${FAILED[@]}"; do
            echo
            echo "===================== $name log ====================="
            cat "$LOGDIR/$name.log"
        done
        echo >&2
        echo "BUILD FAILED: ${FAILED[*]} (logs under $LOGDIR)" >&2
        exit 1
    fi
fi

# ---------- summary -----------------------------------------------------------

step "All packages built"
printf "  manual       : %s\n" "$MANUAL"
printf "  wheel        : %s\n" "$(wheel_in_dist)"
printf "  pyinstaller  : %s\n" "$PYI_BIN"
printf "  flatpak      : %s\n" "$FLATPAK_BUNDLE"
printf "  appimage     : %s\n" "$(appimage_in_dist)"
printf "  release_note : %s\n" "$RELEASE_NOTE"
