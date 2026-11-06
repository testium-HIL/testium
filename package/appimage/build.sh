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

# APPIMAGE_APPDIR_TMPFS (set by build_all --ram) bind-mounts a host tmpfs dir at
# the AppDir build path, keeping the ~1 GB AppDir churn off slow storage.
APPDIR_MOUNT=""
if [ -n "$APPIMAGE_APPDIR_TMPFS" ]; then
    mkdir -p "$APPIMAGE_APPDIR_TMPFS"
    APPDIR_MOUNT="-v $APPIMAGE_APPDIR_TMPFS:/work/package/appimage/AppDir"
fi

# APPIMAGE_EXTRACT_AND_RUN=1 lets appimagetool run without FUSE in the container.
$RUNTIME run --rm \
    --privileged \
    -e APPIMAGE_EXTRACT_AND_RUN=1 \
    -v "$REPO_ROOT:/work" \
    $APPDIR_MOUNT \
    -w /work/package/appimage \
    debian:trixie bash -c "
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

        # Install appimage-builder in a venv: trixie's system pip fails on
        # one of its old, badly named wheels.
        python3 -m venv /opt/aib
        /opt/aib/bin/pip install --quiet --upgrade pip
        /opt/aib/bin/pip install --quiet appimage-builder
        # appimage-builder requires apt-key on PATH, removed in trixie; the
        # recipe adds no keys (no key_url), so a no-op stand-in is enough.
        printf '#!/bin/sh\nexit 0\n' > /usr/local/bin/apt-key
        chmod +x /usr/local/bin/apt-key

        # Run the build
        export APP_VERSION=$APP_VERSION
        /opt/aib/bin/appimage-builder --recipe AppImageBuilder.yml --skip-test
    "

APPIMAGE_FILE=$(ls -1t Testium-*-x86_64.AppImage 2>/dev/null | head -1)
echo "Done: ${APPIMAGE_FILE}"

if [ "${1}" = "install" ] && [ -n "${APPIMAGE_FILE}" ]; then
    install -v "${APPIMAGE_FILE}" "${HOME}/.local/bin/testium"
fi
