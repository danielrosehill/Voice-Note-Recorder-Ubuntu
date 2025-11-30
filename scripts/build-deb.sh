#!/bin/bash
# Build Debian package for Voice Note Recorder
#
# This script creates a .deb package that can be installed with:
#   sudo dpkg -i voice-note-recorder_*.deb
#   sudo apt-get install -f  # Install dependencies if needed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

VERSION=$(grep "^version" app/pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
PACKAGE_NAME="voice-note-recorder"
BUILD_DIR="build/deb-build"
INSTALL_DIR="$BUILD_DIR/${PACKAGE_NAME}_${VERSION}-1_all"

echo "Building Voice Note Recorder v${VERSION} Debian package..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$INSTALL_DIR"

# Create directory structure
mkdir -p "$INSTALL_DIR/DEBIAN"
mkdir -p "$INSTALL_DIR/opt/voice-note-recorder"
mkdir -p "$INSTALL_DIR/usr/bin"
mkdir -p "$INSTALL_DIR/usr/share/applications"
mkdir -p "$INSTALL_DIR/usr/share/icons/hicolor/scalable/apps"

# Copy application files with proper permissions
cp -r app/src/voice_note_recorder "$INSTALL_DIR/opt/voice-note-recorder/"
cp app/pyproject.toml "$INSTALL_DIR/opt/voice-note-recorder/"

# Ensure all files are readable
find "$INSTALL_DIR/opt/voice-note-recorder" -type f -exec chmod 644 {} \;
find "$INSTALL_DIR/opt/voice-note-recorder" -type d -exec chmod 755 {} \;

# Create launcher script
cat > "$INSTALL_DIR/usr/bin/voice-note-recorder" << 'EOF'
#!/bin/bash
# Voice Note Recorder launcher
exec python3 -c "
import sys
sys.path.insert(0, '/opt/voice-note-recorder')
from voice_note_recorder.main import main
main()
"
EOF
chmod +x "$INSTALL_DIR/usr/bin/voice-note-recorder"

# Copy desktop file (ensure readable)
install -m 644 packaging/debian/voice-note-recorder.desktop "$INSTALL_DIR/usr/share/applications/"

# Copy icon (ensure readable)
install -m 644 assets/voice-note-recorder.svg "$INSTALL_DIR/usr/share/icons/hicolor/scalable/apps/"

# Create control file
cat > "$INSTALL_DIR/DEBIAN/control" << EOF
Package: voice-note-recorder
Version: ${VERSION}-1
Section: sound
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyqt6, python3-numpy, python3-soundfile, libportaudio2
Recommends: python3-sounddevice
Maintainer: Daniel Rosehill <public@danielrosehill.com>
Description: Lightweight voice note recorder for AI transcription
 A purpose-built voice note recorder optimized for speech-to-text
 workflows. Pre-configured with settings tuned for STT models like
 Gemini and Whisper, including 16kHz mono audio output.
 .
 Features:
  - Simple record/pause/stop interface
  - Volume meter with target range indicators
  - One-click save to default location (Ctrl+S)
  - Persistent microphone and path preferences
  - Dark theme UI
EOF

# Create postinst script to update icon cache
cat > "$INSTALL_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Update icon cache
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi

# Update desktop database
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi

# Install Python packages if not available system-wide
if ! python3 -c "import sounddevice" 2>/dev/null; then
    echo "Note: python3-sounddevice not found. Installing via pip..."
    pip3 install --break-system-packages sounddevice 2>/dev/null || \
    pip3 install sounddevice 2>/dev/null || \
    echo "Warning: Could not install sounddevice. Please install manually: pip3 install sounddevice"
fi

exit 0
EOF
chmod +x "$INSTALL_DIR/DEBIAN/postinst"

# Create postrm script
cat > "$INSTALL_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

# Update icon cache
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi

# Update desktop database
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi

exit 0
EOF
chmod +x "$INSTALL_DIR/DEBIAN/postrm"

# Build the package
echo "Building package..."
dpkg-deb --root-owner-group --build "$INSTALL_DIR"

# Move to output directory
mkdir -p dist
mv "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}-1_all.deb" dist/

echo ""
echo "Package built successfully!"
echo "Location: dist/${PACKAGE_NAME}_${VERSION}-1_all.deb"
echo ""
echo "Install with:"
echo "  sudo dpkg -i dist/${PACKAGE_NAME}_${VERSION}-1_all.deb"
echo "  sudo apt-get install -f  # If dependencies are missing"
