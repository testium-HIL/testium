#!/bin/bash

# Prérequis : installer le runtime et SDK KDE
# flatpak install flathub org.kde.Platform//6.10
# flatpak install flathub org.kde.Sdk//6.10
# flatpak install flathub io.qt.PySide.BaseApp//6.10

set -e

# Build + install local. FLATPAK_BUILDDIR / FLATPAK_STATEDIR / FLATPAK_REPODIR
# (set by build_all --ram) redirect the build dir, the state dir
# (.flatpak-builder) and the ostree repo to tmpfs. flatpak-builder hardlinks
# between the state dir and the build dir, so they MUST be on the same
# filesystem — hence the state dir moves to tmpfs too (its download cache then
# doesn't persist across --ram runs).
BUILDDIR="${FLATPAK_BUILDDIR:-build}"
STATEDIR="${FLATPAK_STATEDIR:-.flatpak-builder}"
REPODIR="${FLATPAK_REPODIR:-repo}"
flatpak-builder --user --verbose --force-clean --install --state-dir="$STATEDIR" --repo="$REPODIR" "$BUILDDIR" org.testium.Testium.yaml

# Génère le bundle distribuable
flatpak build-bundle "$REPODIR" testium.flatpak org.testium.Testium
echo "Bundle généré : $(pwd)/testium.flatpak"

# Crée ~/.local/bin/testium pour pouvoir taper "testium" en console
WRAPPER="$HOME/.local/bin/testium"
mkdir -p "$HOME/.local/bin"
cat > "$WRAPPER" <<'EOF'
#!/bin/sh
exec flatpak run org.testium.Testium "$@"
EOF
chmod +x "$WRAPPER"
echo "Wrapper installé : $WRAPPER"
echo "Assurez-vous que ~/.local/bin est dans votre PATH."
