# Voice Note Recorder

A lightweight voice note recorder optimized for AI transcription workflows.

## Features

- **STT-Optimized Output**: Records MP3 files optimized for Gemini, Whisper, and other STT APIs
- **Quality Presets**: Choose between Standard (64kbps), Extended (32kbps), or Maximum Duration (24kbps)
- **Simple Controls**: Record, Pause, Stop, Clear
- **Volume Meter**: Averaged level display with target range indicators
- **Quick Save**: One-click save to default location or custom path
- **Microphone Selection**: Choose any available input device
- **Persistent Settings**: Remembers your preferences

## Requirements

- **ffmpeg**: Required for MP3 encoding. Install with `sudo apt install ffmpeg`

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

Recordings are saved as MP3 with configurable quality:

| Preset | Sample Rate | Bitrate | ~Duration per 20MB |
|--------|-------------|---------|-------------------|
| Standard | 16 kHz | 64 kbps | ~43 min |
| Extended | 16 kHz | 32 kbps | ~85 min |
| Maximum | 8 kHz | 24 kbps | ~110 min |

All presets exceed Gemini's internal 16kbps resolution, so there's no transcription quality loss.
