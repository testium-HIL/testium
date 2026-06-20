#!/bin/bash
# Runs the testium validation suite against any installable channel of
# testium (source, wheel, pyinstaller, flatpak, appimage).
#
# Usage:
#   ./test/validation/run.sh [clean] [--mode MODE] [--gui] [extra testium args]
#
#   clean           remove the validation venv before recreating it
#                   (must be the first argument; useful after a Python upgrade)
#
#   --gui           open the GUI with the suite loaded instead of running in
#                   batch; run it manually from the window, which stays open
#                   (handy to inspect the tree, try the Ctrl+F search, ...)
#
#   --mode MODE     which testium build to validate. One of:
#                       source       (default) src/testium via project run.sh
#                       wheel        dist/testium-<v>-py3-none-any.whl
#                       pyinstaller  dist/testium-<v>
#                       flatpak      installed org.testium.Testium
#                       appimage     dist/Testium-<v>-*.AppImage
#
# Every test-execution subprocess (inline <| ... |>, py_func, cycle,
# post_execution, ...) runs in a dedicated host venv under
# /tmp/testium-validation-venv. That venv is shared across modes —
# even Flatpak reaches it via flatpak-spawn --host. The validation venv
# is created with --system-site-packages so existing system packages
# (PySide6, lxml, ...) stay visible, then junit-xml is pip-installed
# for post_execution.py and pytest for the `pytest` item.
#
# The report file is suffixed with the mode (e.g. validation-flatpak.sqlite)
# so consecutive runs in different modes don't overwrite each other.

set -e

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(realpath "$(dirname "$SCRIPT_PATH")")"
PROJECT_DIR="$(realpath "$SCRIPT_DIR/../..")"
VERSION="$(cat "$PROJECT_DIR/src/VERSION")"

# ---------- arg parsing -------------------------------------------------------

MODE=source

if [ "${1:-}" = "clean" ]; then
    CLEAN=1
    shift
else
    CLEAN=0
fi

EXTRA=()
RUN_FLAGS=(-b)            # batch by default; --gui opens the GUI and stays open
GUI=0
while [ $# -gt 0 ]; do
    case "$1" in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --mode=*)
            MODE="${1#--mode=}"
            shift
            ;;
        --gui)
            GUI=1
            RUN_FLAGS=()     # no -b: launch the GUI with the suite loaded,
            shift            # run it manually; the window does not auto-close
            ;;
        *)
            EXTRA+=("$1")
            shift
            ;;
    esac
done

# ---------- validation venv ---------------------------------------------------

VENV_DIR="${TMPDIR:-/tmp}/testium-validation-venv"
if [ "$CLEAN" -eq 1 ]; then
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating validation venv at $VENV_DIR"
    python3 -m venv --system-site-packages "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet junit-xml pytest jsonschema pyyaml
fi
VENV_PYTHON="$VENV_DIR/bin/python3"

# ---------- per-mode launcher -------------------------------------------------

case "$MODE" in
    source)
        CMD=("$PROJECT_DIR/run.sh")
        ;;
    wheel)
        WHEEL="$PROJECT_DIR/dist/testium-${VERSION}-py3-none-any.whl"
        if [ ! -f "$WHEEL" ]; then
            echo "ERROR: wheel not found at $WHEEL — run ./build_all.sh first." >&2
            exit 1
        fi
        WHEEL_VENV="${TMPDIR:-/tmp}/testium-wheel-venv-${VERSION}"
        if [ "$CLEAN" -eq 1 ]; then
            rm -rf "$WHEEL_VENV"
        fi
        if [ ! -d "$WHEEL_VENV" ]; then
            echo "Creating wheel venv at $WHEEL_VENV"
            python3 -m venv --system-site-packages "$WHEEL_VENV"
            "$WHEEL_VENV/bin/pip" install --quiet --upgrade pip
            # Install with the [lsp] extra so the wheel channel is validated in
            # its language-server-capable form (pulls pygls), matching how a
            # user enables `testium lsp` from a wheel: pip install testium[lsp].
            "$WHEEL_VENV/bin/pip" install --quiet "${WHEEL}[lsp]"
        fi
        CMD=("$WHEEL_VENV/bin/python" -m testium)
        ;;
    pyinstaller)
        PYI_BIN="$PROJECT_DIR/dist/testium-${VERSION}"
        if [ ! -x "$PYI_BIN" ]; then
            echo "ERROR: PyInstaller binary not found at $PYI_BIN — run ./build_all.sh first." >&2
            exit 1
        fi
        CMD=("$PYI_BIN")
        ;;
    flatpak)
        if ! flatpak info --user org.testium.Testium &>/dev/null \
           && ! flatpak info --system org.testium.Testium &>/dev/null; then
            echo "ERROR: org.testium.Testium is not installed." >&2
            echo "       flatpak install --user $PROJECT_DIR/dist/testium-${VERSION}.flatpak" >&2
            exit 1
        fi
        CMD=(flatpak run --command=testium org.testium.Testium)
        ;;
    appimage)
        APPIMAGE=$(ls -1t "$PROJECT_DIR/dist"/Testium-"${VERSION}"-*.AppImage 2>/dev/null | head -1)
        if [ -z "$APPIMAGE" ] || [ ! -x "$APPIMAGE" ]; then
            echo "ERROR: no AppImage for version $VERSION under $PROJECT_DIR/dist — run ./build_all.sh first." >&2
            exit 1
        fi
        CMD=("$APPIMAGE")
        ;;
    *)
        echo "ERROR: unknown --mode '$MODE'. Expected: source|wheel|pyinstaller|flatpak|appimage." >&2
        exit 1
        ;;
esac

# ---------- launch ------------------------------------------------------------

echo "-- validation mode: $MODE"
echo "-- launch: ${CMD[*]}"

# ---------- LSP check (this exact channel) ------------------------------------
# Verify `testium lsp` / `testium schema` work in the build under test before
# running the suite: schema must keep its nested actions (declarative ACTIONS,
# survives frozen builds) and the language server must start (pygls bundled).
echo "-- LSP check ($MODE)"
"$VENV_PYTHON" "$SCRIPT_DIR/lsp_check.py" "${CMD[@]}"

# ---------- JSON Schema check (this exact channel) ----------------------------
# `testium schema` must emit a valid JSON Schema (draft 2020-12) that matches
# the versioned schema/tum.json (regenerated by hand after PARAMS/ACTIONS
# changes) and that accepts every schema/test_schema/*.tum fixture.
echo "-- schema check ($MODE)"
"$VENV_PYTHON" "$SCRIPT_DIR/schema_check.py" "${CMD[@]}"

# ---------- load-error check (this exact channel) -----------------------------
# Deliberately broken .tum files must fail to load with a specific, located
# message (not a raw traceback): guards the load-time error handling.
echo "-- load-error check ($MODE)"
"$VENV_PYTHON" "$SCRIPT_DIR/load_errors_check.py" "${CMD[@]}"

if [ "$GUI" -eq 1 ]; then
    echo "-- GUI mode: the suite is loaded; press Start to run. Window stays open."
fi

exec "${CMD[@]}" "${RUN_FLAGS[@]}" \
    -d "python_bin=$VENV_PYTHON" \
    -d "validation_report_file=validation-$MODE" \
    -- "$SCRIPT_DIR/main.tum" "${EXTRA[@]}"
