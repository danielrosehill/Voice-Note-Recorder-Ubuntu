#!/bin/bash
# Build script for Voice Note Recorder Debian package
# Usage: ./build-deb.sh

set -e

# Configuration
VERSION="1.0.0"
PACKAGE_NAME="voice-note-recorder"
ARCH="all"
RELEASE="1"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/deb-build"
PACKAGE_DIR="$BUILD_DIR/${PACKAGE_NAME}_${VERSION}-${RELEASE}_${ARCH}"
SOURCE_DIR="$SCRIPT_DIR/app/src"

echo "Building ${PACKAGE_NAME} version ${VERSION}..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Create package directory structure
mkdir -p "$PACKAGE_DIR/DEBIAN"
mkdir -p "$PACKAGE_DIR/opt/voice-note-recorder/voice_note_recorder"
mkdir -p "$PACKAGE_DIR/usr/bin"
mkdir -p "$PACKAGE_DIR/usr/share/applications"
mkdir -p "$PACKAGE_DIR/usr/share/icons/hicolor/scalable/apps"

# Copy source files
echo "Copying source files..."
cp "$SOURCE_DIR/voice_note_recorder/"*.py "$PACKAGE_DIR/opt/voice-note-recorder/voice_note_recorder/"
cp "$SCRIPT_DIR/app/pyproject.toml" "$PACKAGE_DIR/opt/voice-note-recorder/"

# Ensure files are world-readable
chmod 644 "$PACKAGE_DIR/opt/voice-note-recorder/voice_note_recorder/"*.py
chmod 644 "$PACKAGE_DIR/opt/voice-note-recorder/pyproject.toml"

# Create launcher script
cat > "$PACKAGE_DIR/usr/bin/voice-note-recorder" << 'EOF'
#!/bin/bash
# Voice Note Recorder launcher
exec python3 -c "
import sys
sys.path.insert(0, '/opt/voice-note-recorder')
from voice_note_recorder.main import main
main()
"
EOF
chmod 755 "$PACKAGE_DIR/usr/bin/voice-note-recorder"

# Create desktop entry
cat > "$PACKAGE_DIR/usr/share/applications/voice-note-recorder.desktop" << EOF
[Desktop Entry]
Name=Voice Note Recorder
Comment=Lightweight voice note recorder for AI transcription
Exec=voice-note-recorder
Icon=voice-note-recorder
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Recorder;
Keywords=voice;audio;recorder;transcription;stt;speech;
StartupNotify=true
EOF

# Create icon (light theme compatible)
cat > "$PACKAGE_DIR/usr/share/icons/hicolor/scalable/apps/voice-note-recorder.svg" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
  <!-- Background circle -->
  <circle cx="24" cy="24" r="22" fill="#f5f5f5" stroke="#4CAF50" stroke-width="2"/>

  <!-- Microphone body -->
  <rect x="18" y="10" width="12" height="20" rx="6" fill="#4CAF50"/>

  <!-- Microphone stand -->
  <path d="M24 30 L24 38" stroke="#4CAF50" stroke-width="3" stroke-linecap="round"/>
  <path d="M18 38 L30 38" stroke="#4CAF50" stroke-width="3" stroke-linecap="round"/>

  <!-- Sound waves -->
  <path d="M12 20 Q8 24 12 28" stroke="#2196F3" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M36 20 Q40 24 36 28" stroke="#2196F3" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>
EOF

# Create DEBIAN control file
cat > "$PACKAGE_DIR/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}-${RELEASE}
Section: sound
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.10), python3-pyqt6, python3-numpy, python3-soundfile, libportaudio2, ffmpeg
Recommends: python3-sounddevice
Maintainer: Daniel Rosehill <public@danielrosehill.com>
Homepage: https://github.com/danielrosehill/Voice-Note-Recorder-Ubuntu
Description: Lightweight voice note recorder for AI transcription
 A purpose-built voice note recorder optimized for speech-to-text
 workflows. Pre-configured with settings tuned for STT models like
 Gemini and Whisper.
 .
 Features:
  - Simple record/pause/stop interface
  - Volume meter with target range indicators
  - Multiple quality presets (Standard, Extended, Maximum Duration)
  - One-click save to default location (Ctrl+S)
  - Persistent microphone and path preferences
  - Clean, modern minimalist UI
EOF

# Create postinst script
cat > "$PACKAGE_DIR/DEBIAN/postinst" << 'EOF'
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
chmod 755 "$PACKAGE_DIR/DEBIAN/postinst"

# Create postrm script
cat > "$PACKAGE_DIR/DEBIAN/postrm" << 'EOF'
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
chmod 755 "$PACKAGE_DIR/DEBIAN/postrm"

# Build the package
echo "Building Debian package..."
dpkg-deb --root-owner-group --build "$PACKAGE_DIR"

# Move to build directory root
DEB_FILE="${PACKAGE_NAME}_${VERSION}-${RELEASE}_${ARCH}.deb"
mv "$BUILD_DIR/$DEB_FILE" "$BUILD_DIR/../$DEB_FILE"

echo ""
echo "Build complete!"
echo "Package: build/$DEB_FILE"
echo ""
echo "To install: sudo dpkg -i build/$DEB_FILE"
echo "To fix dependencies: sudo apt-get install -f"
