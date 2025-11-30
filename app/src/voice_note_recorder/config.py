"""Configuration and settings management."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# Audio settings optimized for STT (Gemini, Whisper, etc.)
# Target: 16-bit PCM, 16kHz, mono WAV
SAMPLE_RATE = 16000  # 16kHz - native for Gemini Live API
CHANNELS = 1  # Mono
SAMPLE_WIDTH = 2  # 16-bit (2 bytes)
DTYPE = "int16"  # numpy dtype for 16-bit audio

# Volume meter settings
METER_UPDATE_INTERVAL_MS = 100  # Update meter every 100ms
METER_AVERAGING_SECONDS = 10  # Average over 10 seconds for stability
METER_MIN_DB = -60  # Minimum dB level shown
METER_MAX_DB = 0  # Maximum dB level shown
METER_TARGET_MIN_DB = -30  # Target range minimum
METER_TARGET_MAX_DB = -10  # Target range maximum

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "voice-note-recorder"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "settings.json"
DEFAULT_SAVE_PATH = Path.home() / "Voice Notes"


@dataclass
class Settings:
    """Application settings with persistence."""

    default_save_path: str = field(default_factory=lambda: str(DEFAULT_SAVE_PATH))
    preferred_device: Optional[str] = None  # Device name, None = system default

    @classmethod
    def load(cls, config_file: Path = DEFAULT_CONFIG_FILE) -> "Settings":
        """Load settings from file, or return defaults if not found."""
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return cls()

    def save(self, config_file: Path = DEFAULT_CONFIG_FILE) -> None:
        """Save settings to file."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def get_save_path(self) -> Path:
        """Get the default save path, creating it if necessary."""
        path = Path(self.default_save_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
