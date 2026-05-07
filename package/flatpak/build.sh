#!/bin/bash

# Prérequis : installer le runtime et SDK KDE
# flatpak install flathub org.kde.Platform//6.10
# flatpak install flathub org.kde.Sdk//6.10
# flatpak install flathub io.qt.PySide.BaseApp//6.10

set -e

# Build + install local
flatpak-builder --user --verbose --force-clean --install --repo=repo build org.testium.Testium.yaml

# Génère le bundle distribuable
flatpak build-bundle repo testium.flatpak org.testium.Testium
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
