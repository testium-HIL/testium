#!/usr/bin/env bash
# test_distro.sh — verify testium runs on a target Debian/Ubuntu distrib.
#
# Spins up a Docker container of the requested image, checks which expected
# system Python packages are available (apt), installs them, installs the
# testium wheel, and runs a smoke test that exercises batch mode + py_func
# subprocess.
#
# Usage:
#   ./test_distro.sh debian:bookworm
#   ./test_distro.sh debian:trixie
#   ./test_distro.sh ubuntu:24.04

set -euo pipefail

IMAGE="${1:?Usage: $0 <image>  e.g. debian:bookworm | debian:trixie | ubuntu:24.04}"
ROOT=$(realpath "$(dirname "$0")/../..")

# Container runtime: prefer docker if available, fall back to podman
if command -v docker >/dev/null 2>&1; then
    CTR=docker
elif command -v podman >/dev/null 2>&1; then
    CTR=podman
else
    echo "ERROR: neither docker nor podman is installed" >&2
    exit 1
fi
echo "[host] Using $CTR"

# --- Build the wheel on the host if it does not already exist
WHEEL_DIR="$ROOT/src/dist"
PYTHON_HOST="$ROOT/test/tmp/.venv/bin/python3"
[ -x "$PYTHON_HOST" ] || PYTHON_HOST=python3
if ! ls "$WHEEL_DIR"/testium-*.whl >/dev/null 2>&1; then
    echo "[host] Building wheel..."
    (cd "$ROOT/src" && "$PYTHON_HOST" -m build --wheel >/dev/null)
fi
WHEEL=$(ls "$WHEEL_DIR"/testium-*.whl | head -1)
WHEEL_NAME=$(basename "$WHEEL")
echo "[host] Using $WHEEL_NAME"

# Expected system Python packages on the target distrib
APT_PACKAGES=(
    python3
    python3-pip
    python3-setuptools
    python3-pyside6.qtwidgets
    python3-yaml
    python3-jinja2
    python3-colorama
    python3-git
    python3-pexpect
    python3-matplotlib
    python3-lxml
    python3-serial
    python3-telnetlib3
    lua5.4
    lua-cjson
    lua-socket
    git
)

echo "=== Testing on $IMAGE ==="

$CTR run --rm \
    -v "$ROOT:/testium:ro" \
    -e WHEEL_NAME="$WHEEL_NAME" \
    -e PACKAGES="${APT_PACKAGES[*]}" \
    "$IMAGE" \
    bash -c '
        set -e
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq

        # 1. Availability check
        echo
        echo "--- System package availability ---"
        AVAILABLE=()
        MISSING=()
        for pkg in $PACKAGES; do
            if apt-cache show "$pkg" >/dev/null 2>&1; then
                AVAILABLE+=("$pkg")
                echo "  OK     $pkg"
            else
                MISSING+=("$pkg")
                echo "  MISSING $pkg"
            fi
        done
        echo

        # 2. Install available packages
        echo "--- Installing system packages ---"
        apt-get install -qq -y --no-install-recommends "${AVAILABLE[@]}" ca-certificates >/dev/null

        # 3. Map missing apt packages to their PyPI equivalents and pip-install
        #    them as a fallback (kept minimal so the run is still a "system"
        #    install for the most part)
        declare -A PIP_FALLBACK=(
            [python3-pyside6.qtwidgets]=pyside6
            [python3-telnetlib3]=telnetlib3
        )
        # junit_xml has no Debian package — install it via pip so the
        # validation post_execution.py can import it.
        EXTRA_PIP=(junit-xml)
        PIP_PKGS=()
        for m in "${MISSING[@]}"; do
            fallback="${PIP_FALLBACK[$m]:-}"
            if [ -n "$fallback" ]; then
                PIP_PKGS+=("$fallback")
            fi
        done
        PIP_PKGS+=("${EXTRA_PIP[@]}")
        if [ ${#PIP_PKGS[@]} -gt 0 ]; then
            echo "--- Installing missing deps via pip: ${PIP_PKGS[*]} ---"
            pip install --break-system-packages "${PIP_PKGS[@]}" >/dev/null
        fi

        # 4. Install testium wheel
        echo "--- Installing testium wheel ---"
        pip install --break-system-packages --no-deps "/testium/src/dist/$WHEEL_NAME" >/dev/null

        # 5. Install the fake_exporter plugin (needed by the report_plugin
        #    validation test which exercises entry-points discovery).
        #    Copy it first because /testium is mounted read-only and the
        #    setuptools backend touches its build dir.
        echo "--- Installing testium-fake-exporter (test plugin) ---"
        cp -r /testium/test/validation/fake_exporter /tmp/fake_exporter
        pip install --break-system-packages /tmp/fake_exporter >/dev/null

        # 6. Run the full validation suite. Outputs are streamed live so
        #    progress is visible — the suite takes a couple of minutes.
        #    Reports go to /tmp/testium-validation since /testium is RO.
        echo "--- Running validation suite ---"
        mkdir -p /tmp/testium-validation
        cd /testium
        testium -b -o \
            -d "validation_report_path=/tmp/testium-validation/" \
            -- test/validation/main.tum
    '

echo "=== $IMAGE: PASS ==="
