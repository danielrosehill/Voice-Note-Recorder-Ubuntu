# Voice Note Recorder for Ubuntu

A lightweight, purpose-built voice note recorder optimized for AI transcription workflows.

## Problem Statement

Existing voice recorders fall into two categories:
1. **Overkill**: DAWs like Audacity with unnecessary complexity
2. **Oversimplified**: Basic recorders lacking essential controls

Neither is optimized for voice notes destined for speech-to-text processing.

## Core Concept

A recorder pre-optimized for voice note capture with settings tuned for STT models (Gemini, Whisper, etc.) rather than high-fidelity audio production.

---

## Technical Requirements

### Audio Encoding

- **Format**: Mono audio (not stereo)
- **Bit rate**: Match Gemini API limits (refer to current docs for exact spec)
- **Container**: Lightweight format suitable for STT ingestion
- **Goal**: Preserve intelligibility while minimizing file size

### Microphone Handling

- Default to system default microphone
- Allow user override with persistent preference
- Handle high-bitrate input devices (e.g., Samson Q2U) with automatic downsampling

---

## UI Specification

### Main Controls

| Button | Function |
|--------|----------|
| **Record** | Start recording |
| **Pause** | Pause/resume recording |
| **Stop** | End recording session |
| **X** | Clear recording from cache (retake) |

### Save Options

After recording, display two save buttons:
- **Save to Default** — One-click save to configured default path
- **Save to Custom** — Opens file browser for custom location

### Audio Level Display

- **Volume meter** showing input level (averaged over ~10 seconds to reduce jumpiness)
- **Target range indicators** — Two notches showing min/max recommended levels
- **No waveform display** — Intentionally excluded to reduce distraction

### Settings Interface

- Default save path configuration
- Microphone selection dropdown
- Preferences persisted to lightweight local storage

---

## Development Plan

### Phase 1: Validation
- Build minimal viable UI with core recording functionality
- Validate audio encoding settings against Gemini API requirements
- Test with target microphone (Samson Q2U)

### Phase 2: Feature Iteration
- Add pause/resume functionality
- Implement settings persistence
- Refine volume meter UX

### Phase 3: Packaging
- Create Debian package build script
- Create update script for rebuilding and upgrading local installation

---

## Technical Decisions (To Research)

- [ ] Confirm Gemini STT bitrate/format requirements
- [ ] Select audio backend (PipeWire/PulseAudio integration)
- [ ] Choose GUI framework (Qt/GTK for native KDE integration)
- [ ] Define preferences storage format/location

---

## Design Principles

- **Pragmatic and functional** — No unnecessary visual flourishes
- **Pre-optimized defaults** — Sane settings out of the box for STT workflows
- **Minimal friction** — Quick record → save workflow
- **Distraction-free** — Volume meter over waveform; clean interface
