"""Configuration and settings management."""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class QualityPreset(Enum):
    """Audio quality presets optimized for different use cases."""

    STANDARD = "standard"      # Best quality, ~11 min per 20MB
    EXTENDED = "extended"      # Good quality, ~22 min per 20MB
    MAXIMUM = "maximum"        # Telephone quality, ~44 min per 20MB


@dataclass
class QualitySettings:
    """Audio settings for a quality preset."""

    name: str
    sample_rate: int
    sample_width: int  # Bytes (1=8-bit, 2=16-bit)
    dtype: str         # numpy dtype
    subtype: str       # soundfile subtype for WAV
    description: str
    max_duration_str: str  # Human-readable max duration

    @property
    def bytes_per_second(self) -> int:
        """Calculate bytes per second for this preset."""
        return self.sample_rate * self.sample_width  # Mono

    @property
    def max_duration_seconds(self) -> int:
        """Calculate max duration in seconds for 20MB."""
        return (GEMINI_MAX_FILE_SIZE_MB * 1024 * 1024) // self.bytes_per_second


# Quality preset definitions
QUALITY_PRESETS: dict[QualityPreset, QualitySettings] = {
    QualityPreset.STANDARD: QualitySettings(
        name="Standard",
        sample_rate=16000,   # 16kHz
        sample_width=2,      # 16-bit
        dtype="int16",
        subtype="PCM_16",
        description="Best clarity for voice. Native format for Gemini/Whisper.",
        max_duration_str="~11 minutes",
    ),
    QualityPreset.EXTENDED: QualitySettings(
        name="Extended",
        sample_rate=8000,    # 8kHz
        sample_width=2,      # 16-bit
        dtype="int16",
        subtype="PCM_16",
        description="Good quality for longer recordings. Still very clear.",
        max_duration_str="~22 minutes",
    ),
    QualityPreset.MAXIMUM: QualitySettings(
        name="Maximum Duration",
        sample_rate=8000,    # 8kHz
        sample_width=1,      # 8-bit (unsigned)
        dtype="uint8",
        subtype="PCM_U8",
        description="Telephone quality. Use for very long voice notes.",
        max_duration_str="~44 minutes",
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
