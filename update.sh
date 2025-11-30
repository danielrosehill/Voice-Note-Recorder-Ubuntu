#!/bin/bash
# Update Voice Note Recorder
#
# Rebuilds the Debian package and upgrades the local installation.
# Usage: ./update.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Voice Note Recorder Update ==="
echo ""

# Check current version
if dpkg -l voice-note-recorder 2>/dev/null | grep -q "^ii"; then
    CURRENT=$(dpkg -l voice-note-recorder | grep "^ii" | awk '{print $3}')
    echo "Currently installed: $CURRENT"
else
    echo "Not currently installed. Use ./install.sh instead."
    exit 1
fi

# Get new version
NEW_VERSION=$(grep "^version" app/pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
echo "Building version: $NEW_VERSION"
echo ""

# Build the package
./scripts/build-deb.sh

DEB_FILE="dist/voice-note-recorder_${NEW_VERSION}-1_all.deb"

if [ ! -f "$DEB_FILE" ]; then
    echo "Error: Package file not found: $DEB_FILE"
    exit 1
fi

echo ""
read -p "Install update? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Skipping installation. Package available at: $DEB_FILE"
    exit 0
fi

echo "Installing update..."
sudo dpkg -i "$DEB_FILE"
sudo apt-get install -f -y 2>/dev/null || true

echo ""
echo "Update complete!"

if dpkg -l voice-note-recorder 2>/dev/null | grep -q "^ii"; then
    INSTALLED=$(dpkg -l voice-note-recorder | grep "^ii" | awk '{print $3}')
    echo "Installed version: $INSTALLED"
fi
