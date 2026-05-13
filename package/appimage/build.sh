#!/bin/bash
# Build the testium AppImage inside a Debian container (Podman or Docker).
# The resulting .AppImage file is written to this directory.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_VERSION="$(<"$REPO_ROOT/src/VERSION")"

if command -v podman &>/dev/null; then
    RUNTIME=podman
elif command -v docker &>/dev/null; then
    RUNTIME=docker
else
    echo "Error: neither podman nor docker found." >&2
    exit 1
fi
echo "Using $RUNTIME — building testium $APP_VERSION AppImage..."

# APPIMAGE_EXTRACT_AND_RUN=1 lets appimagetool run without FUSE in the container.
$RUNTIME run --rm \
    --privileged \
    -e APPIMAGE_EXTRACT_AND_RUN=1 \
    -v "$REPO_ROOT:/work" \
    -w /work/package/appimage \
    debian:bookworm bash -c "
        set -e
        export DEBIAN_FRONTEND=noninteractive

        apt-get update -qq
        apt-get install -y -qq \
            python3 python3-pip python3-venv python3-build \
            dpkg-dev fakeroot squashfs-tools wget curl file binutils \
            libglib2.0-0 patchelf zsync > /dev/null

        # Build the wheel
        cd /work/src
        python3 -m build --wheel --outdir dist/ > /dev/null
        cd /work/package/appimage

        # Install appimage-builder
        pip3 install appimage-builder --quiet --break-system-packages

        # Run the build
        export APP_VERSION=$APP_VERSION
        appimage-builder --recipe AppImageBuilder.yml --skip-test
    "

APPIMAGE_FILE=$(ls -1t Testium-*-x86_64.AppImage 2>/dev/null | head -1)
echo "Done: ${APPIMAGE_FILE}"

if [ "${1}" = "install" ] && [ -n "${APPIMAGE_FILE}" ]; then
    install -v "${APPIMAGE_FILE}" "${HOME}/.local/bin/testium"
fi
