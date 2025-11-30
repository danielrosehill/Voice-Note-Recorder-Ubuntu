#!/bin/bash
# Install Voice Note Recorder
#
# Builds the Debian package and installs it.
# Usage: ./install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Voice Note Recorder Installation ==="
echo ""

# Build the package
./scripts/build-deb.sh

# Get version
VERSION=$(grep "^version" app/pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
DEB_FILE="dist/voice-note-recorder_${VERSION}-1_all.deb"

if [ ! -f "$DEB_FILE" ]; then
    echo "Error: Package file not found: $DEB_FILE"
    exit 1
fi

echo ""
echo "Installing package..."
sudo dpkg -i "$DEB_FILE"

# Fix any missing dependencies
sudo apt-get install -f -y 2>/dev/null || true

echo ""
echo "Installation complete!"
echo ""

# Verify
if dpkg -l voice-note-recorder 2>/dev/null | grep -q "^ii"; then
    INSTALLED=$(dpkg -l voice-note-recorder | grep "^ii" | awk '{print $3}')
    echo "Installed version: $INSTALLED"
fi

echo ""
echo "Launch with: voice-note-recorder"
echo "Or find 'Voice Note Recorder' in your application menu."
