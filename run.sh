#!/usr/bin/env bash
# Voice Note Recorder launcher script
# Handles venv activation and runs the app

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"
VENV_DIR="$APP_DIR/.venv"

# Check if venv exists, create if not
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    cd "$APP_DIR"
    uv venv .venv
    source "$VENV_DIR/bin/activate"
    uv pip install -e .
else
    source "$VENV_DIR/bin/activate"
fi

# Run the application
exec python -m voice_note_recorder.main "$@"
