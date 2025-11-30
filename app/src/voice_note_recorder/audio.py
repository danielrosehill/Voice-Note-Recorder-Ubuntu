"""Audio recording module using sounddevice."""

import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import CHANNELS, QualitySettings, get_quality_settings


class RecordingState(Enum):
    """Recording state machine states."""
    IDLE = auto()
    RECORDING = auto()
    PAUSED = auto()
    STOPPED = auto()  # Recording finished, ready to save


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    index: int
    name: str
    channels: int
    sample_rate: float
    is_default: bool = False


class AudioRecorder:
    """
    Audio recorder optimized for voice notes.

    Records mono audio with configurable quality settings for STT models.
    """

    def __init__(
        self,
        level_callback: Optional[Callable[[float], None]] = None,
        quality_settings: Optional[QualitySettings] = None,
    ):
        """
        Initialize the recorder.

        Args:
            level_callback: Optional callback for audio level updates (dB value)
            quality_settings: Audio quality settings (defaults to default preset)
        """
        self._state = RecordingState.IDLE
        self._audio_queue: queue.Queue = queue.Queue()
        self._recorded_frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._recording_thread: Optional[threading.Thread] = None
        self._level_callback = level_callback
        self._device_index: Optional[int] = None
        self._lock = threading.Lock()
        self._quality = quality_settings or get_quality_settings()

    def set_quality(self, quality_settings: QualitySettings) -> None:
        """
        Set the quality settings for recording.

        Can only be changed when not recording.
        """
        if self._state != RecordingState.IDLE:
            raise RuntimeError("Cannot change quality while recording")
        self._quality = quality_settings

    @property
    def state(self) -> RecordingState:
        """Current recording state."""
        return self._state

    @property
    def quality(self) -> QualitySettings:
        """Current quality settings."""
        return self._quality

    @staticmethod
    def list_devices() -> list[AudioDevice]:
        """List available audio input devices."""
        devices = []
        default_device = sd.default.device[0]  # Input device index

        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append(AudioDevice(
                    index=i,
                    name=dev["name"],
                    channels=dev["max_input_channels"],
                    sample_rate=dev["default_samplerate"],
                    is_default=(i == default_device)
                ))

        return devices

    def set_device(self, device_index: Optional[int] = None) -> None:
        """
        Set the recording device.

        Args:
            device_index: Device index, or None for system default
        """
        self._device_index = device_index

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback for audio stream - runs in separate thread."""
        if status:
            print(f"Audio callback status: {status}")

        # Always calculate level for meter (even when paused)
        if self._level_callback:
            # Calculate RMS and convert to dB
            # Normalize based on bit depth
            if self._quality.sample_width == 1:
                # 8-bit unsigned: 0-255, center at 128
                rms = np.sqrt(np.mean((indata.astype(np.float32) - 128) ** 2))
                max_val = 128
            else:
                # 16-bit signed: -32768 to 32767
                rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
                max_val = 32768

            if rms > 0:
                db = 20 * np.log10(rms / max_val)
            else:
                db = -100
            self._level_callback(db)

        # Only queue audio if actively recording (not paused)
        if self._state == RecordingState.RECORDING:
            self._audio_queue.put(indata.copy())

    def _recording_loop(self) -> None:
        """Background thread that collects audio from queue."""
        while self._state in (RecordingState.RECORDING, RecordingState.PAUSED):
            try:
                data = self._audio_queue.get(timeout=0.1)
                if self._state == RecordingState.RECORDING:
                    with self._lock:
                        self._recorded_frames.append(data)
            except queue.Empty:
                continue

    def start(self) -> None:
        """Start recording."""
        if self._state != RecordingState.IDLE:
            return

        self._recorded_frames = []
        self._state = RecordingState.RECORDING

        # Clear the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start audio stream with current quality settings
        self._stream = sd.InputStream(
            samplerate=self._quality.sample_rate,
            channels=CHANNELS,
            dtype=self._quality.dtype,
            device=self._device_index,
            callback=self._audio_callback,
            blocksize=int(self._quality.sample_rate * 0.1),  # 100ms blocks
        )
        self._stream.start()

        # Start recording thread
        self._recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._recording_thread.start()

    def pause(self) -> None:
        """Pause recording (audio stream continues for level meter)."""
        if self._state == RecordingState.RECORDING:
            self._state = RecordingState.PAUSED

    def resume(self) -> None:
        """Resume recording."""
        if self._state == RecordingState.PAUSED:
            self._state = RecordingState.RECORDING

    def stop(self) -> None:
        """Stop recording (keeps audio data for saving)."""
        if self._state in (RecordingState.RECORDING, RecordingState.PAUSED):
            self._state = RecordingState.STOPPED

            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if self._recording_thread:
                self._recording_thread.join(timeout=1.0)
                self._recording_thread = None

    def clear(self) -> None:
        """Clear recorded audio and return to idle state."""
        self.stop()
        with self._lock:
            self._recorded_frames = []
        self._state = RecordingState.IDLE

    def get_duration(self) -> float:
        """Get current recording duration in seconds."""
        with self._lock:
            if not self._recorded_frames:
                return 0.0
            total_frames = sum(len(f) for f in self._recorded_frames)
        return total_frames / self._quality.sample_rate

    def save(self, filepath: Path) -> Path:
        """
        Save the recording to a WAV file.

        Args:
            filepath: Path to save the file (without extension)

        Returns:
            The actual path where the file was saved
        """
        if self._state != RecordingState.STOPPED:
            raise RuntimeError("Cannot save: recording not stopped")

        with self._lock:
            if not self._recorded_frames:
                raise RuntimeError("Cannot save: no audio recorded")

            # Concatenate all frames
            audio_data = np.concatenate(self._recorded_frames, axis=0)

        # Ensure .wav extension
        filepath = filepath.with_suffix(".wav")

        # Save with current quality settings
        sf.write(
            filepath,
            audio_data,
            self._quality.sample_rate,
            subtype=self._quality.subtype,
        )

        # Return to idle state after saving
        self._recorded_frames = []
        self._state = RecordingState.IDLE

        return filepath

    def generate_filename(self) -> str:
        """Generate a timestamped filename."""
        return datetime.now().strftime("voice_note_%Y%m%d_%H%M%S")
