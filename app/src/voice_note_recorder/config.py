"""Configuration and settings management."""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class QualityPreset(Enum):
    """Audio quality presets optimized for STT workflows (all MP3 output)."""

    STANDARD = "standard"      # Best quality, ~43 min per 20MB (64kbps)
    EXTENDED = "extended"      # Good quality, ~85 min per 20MB (32kbps)
    MAXIMUM = "maximum"        # Telephone quality, ~110 min per 20MB (24kbps)


@dataclass
class QualitySettings:
    """Audio settings for a quality preset."""

    name: str
    sample_rate: int
    mp3_bitrate: int   # kbps for MP3 encoding
    description: str
    max_duration_str: str  # Human-readable max duration

    # Internal recording format (always 16-bit for best quality before MP3 encoding)
    sample_width: int = 2  # Bytes (always 16-bit for recording)
    dtype: str = "int16"   # numpy dtype

    @property
    def bytes_per_second_mp3(self) -> int:
        """Calculate bytes per second for MP3 output."""
        return (self.mp3_bitrate * 1000) // 8  # kbps to bytes/sec

    @property
    def max_duration_seconds(self) -> int:
        """Calculate max duration in seconds for 20MB."""
        return (GEMINI_MAX_FILE_SIZE_MB * 1024 * 1024) // self.bytes_per_second_mp3


# Quality preset definitions (all MP3 output)
QUALITY_PRESETS: dict[QualityPreset, QualitySettings] = {
    QualityPreset.STANDARD: QualitySettings(
        name="Standard",
        sample_rate=16000,   # 16kHz - native for STT models
        mp3_bitrate=64,      # 64 kbps - excellent for voice
        description="Best clarity for voice. Native format for Gemini/Whisper.",
        max_duration_str="~43 minutes",
    ),
    QualityPreset.EXTENDED: QualitySettings(
        name="Extended",
        sample_rate=16000,   # 16kHz - keep good sample rate
        mp3_bitrate=32,      # 32 kbps - still exceeds Gemini's 16kbps internal
        description="Good quality for longer recordings. Still very clear.",
        max_duration_str="~85 minutes",
    ),
    QualityPreset.MAXIMUM: QualitySettings(
        name="Maximum Duration",
        sample_rate=8000,    # 8kHz - telephone quality
        mp3_bitrate=24,      # 24 kbps - minimum reasonable for speech
        description="Telephone quality. Use for very long voice notes.",
        max_duration_str="~110 minutes",
    ),
}

# Default preset
DEFAULT_QUALITY_PRESET = QualityPreset.EXTENDED

# Convenience: get settings for default preset
def get_quality_settings(preset: QualityPreset = DEFAULT_QUALITY_PRESET) -> QualitySettings:
    """Get the QualitySettings for a given preset."""
    return QUALITY_PRESETS[preset]

# Legacy constants for backward compatibility (default preset)
CHANNELS = 1  # Always mono

# Gemini API file size limit
GEMINI_MAX_FILE_SIZE_MB = 20

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
    quality_preset: str = field(default_factory=lambda: DEFAULT_QUALITY_PRESET.value)

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

    def get_quality_preset(self) -> QualityPreset:
        """Get the current quality preset as enum."""
        try:
            return QualityPreset(self.quality_preset)
        except ValueError:
            return DEFAULT_QUALITY_PRESET

    def get_quality_settings(self) -> QualitySettings:
        """Get the current quality settings."""
        return QUALITY_PRESETS[self.get_quality_preset()]
