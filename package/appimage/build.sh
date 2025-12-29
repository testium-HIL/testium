#!/usr/bin/bash

export APP_VERSION=$(<../../src/VERSION)

appimage-builder --recipe AppImageBuilder.yml

RESULT=$?
if [ -n "$1" ] && [ "$1" = "install" ]; then
    if [ $RESULT -eq 0 ]; then
        install -v "testium-${APP_VERSION}-x86_64.AppImage" "${HOME}/.local/bin/testium"
    fi
fi
