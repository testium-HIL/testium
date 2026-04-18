#!/bin/bash

# Prérequis : installer le runtime et SDK KDE
# flatpak install flathub org.kde.Platform//6.10
# flatpak install flathub org.kde.Sdk//6.10
# flatpak install flathub io.qt.PySide.BaseApp//6.10

flatpak-builder --user --verbose --force-clean --install build org.testium.Testium.yaml
