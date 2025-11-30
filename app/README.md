# Voice Note Recorder

A lightweight voice note recorder optimized for AI transcription workflows.

## Features

- **STT-Optimized Output**: Records 16-bit PCM, 16kHz mono WAV files - the native format for Gemini Live API and optimal for Whisper
- **Simple Controls**: Record, Pause, Stop, Clear
- **Volume Meter**: Averaged level display with target range indicators
- **Quick Save**: One-click save to default location or custom path
- **Microphone Selection**: Choose any available input device
- **Persistent Settings**: Remembers your preferences

## Installation

```bash
cd app
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

## Usage

```bash
voice-note-recorder
```

## Audio Format

Recordings are saved as:
- **Format**: WAV (PCM)
- **Sample Rate**: 16kHz
- **Bit Depth**: 16-bit
- **Channels**: Mono

This format is optimized for speech-to-text APIs while keeping file sizes small.
