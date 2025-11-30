"""Main UI window for the voice note recorder."""

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QFrame,
    QSizePolicy,
)

from .audio import AudioRecorder, RecordingState
from .config import Settings, METER_UPDATE_INTERVAL_MS
from .widgets import VolumeMeter


class LevelSignal(QObject):
    """Signal bridge for thread-safe level updates."""
    level_changed = pyqtSignal(float)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.settings = Settings.load()
        self._level_signal = LevelSignal()
        self._level_signal.level_changed.connect(self._on_level_update)

        self.recorder = AudioRecorder(
            level_callback=lambda db: self._level_signal.level_changed.emit(db)
        )

        self._setup_ui()
        self._setup_timer()
        self._load_devices()
        self._apply_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Voice Note Recorder")
        self.setMinimumSize(400, 280)
        self.setMaximumSize(500, 350)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Volume meter
        self.volume_meter = VolumeMeter()
        layout.addWidget(self.volume_meter)

        # Duration display
        self.duration_label = QLabel("00:00")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                font-family: monospace;
                color: #e0e0e0;
            }
        """)
        layout.addWidget(self.duration_label)

        # Status label
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Main controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.record_btn = QPushButton("Record")
        self.record_btn.setMinimumHeight(40)
        self.record_btn.clicked.connect(self._on_record)
        self.record_btn.setStyleSheet(self._button_style("#4CAF50", "#45a049"))
        controls_layout.addWidget(self.record_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.clicked.connect(self._on_pause)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet(self._button_style("#FF9800", "#e68a00"))
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._button_style("#f44336", "#da190b"))
        controls_layout.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("X")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setMaximumWidth(50)
        self.clear_btn.clicked.connect(self._on_clear)
        self.clear_btn.setEnabled(False)
        self.clear_btn.setToolTip("Clear recording (retake)")
        self.clear_btn.setStyleSheet(self._button_style("#666", "#555"))
        controls_layout.addWidget(self.clear_btn)

        layout.addLayout(controls_layout)

        # Save controls (initially hidden)
        self.save_frame = QFrame()
        save_layout = QHBoxLayout(self.save_frame)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.setSpacing(8)

        self.save_default_btn = QPushButton("Save to Default")
        self.save_default_btn.setMinimumHeight(36)
        self.save_default_btn.clicked.connect(self._on_save_default)
        self.save_default_btn.setStyleSheet(self._button_style("#2196F3", "#1976D2"))
        save_layout.addWidget(self.save_default_btn)

        self.save_custom_btn = QPushButton("Save to Custom...")
        self.save_custom_btn.setMinimumHeight(36)
        self.save_custom_btn.clicked.connect(self._on_save_custom)
        self.save_custom_btn.setStyleSheet(self._button_style("#607D8B", "#546E7A"))
        save_layout.addWidget(self.save_custom_btn)

        self.save_frame.hide()
        layout.addWidget(self.save_frame)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)

        # Settings section
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(8)

        # Device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("Microphone:")
        device_label.setStyleSheet("color: #aaa;")
        device_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self.device_combo, 1)

        settings_layout.addLayout(device_layout)

        # Save path
        path_layout = QHBoxLayout()
        path_label = QLabel("Save to:")
        path_label.setStyleSheet("color: #aaa;")
        path_layout.addWidget(path_label)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_path)
        path_layout.addWidget(self.browse_btn)

        settings_layout.addLayout(path_layout)

        layout.addLayout(settings_layout)

        # Apply dark theme
        self._apply_theme()

    def _button_style(self, bg_color: str, hover_color: str) -> str:
        """Generate button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #444;
                color: #666;
            }}
        """

    def _apply_theme(self) -> None:
        """Apply dark theme to the window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QComboBox {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                color: #e0e0e0;
                selection-background-color: #555;
            }
            QLineEdit {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #444;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)

    def _setup_timer(self) -> None:
        """Set up the UI update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(METER_UPDATE_INTERVAL_MS)

    def _load_devices(self) -> None:
        """Load available audio devices into the combo box."""
        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        devices = self.recorder.list_devices()
        self._devices = devices

        for dev in devices:
            label = f"{dev.name}"
            if dev.is_default:
                label += " (Default)"
            self.device_combo.addItem(label, dev.index)

        self.device_combo.blockSignals(False)

    def _apply_settings(self) -> None:
        """Apply loaded settings to UI."""
        self.path_edit.setText(self.settings.default_save_path)

        # Select preferred device if set
        if self.settings.preferred_device:
            for i, dev in enumerate(self._devices):
                if dev.name == self.settings.preferred_device:
                    self.device_combo.setCurrentIndex(i)
                    self.recorder.set_device(dev.index)
                    break

    def _on_level_update(self, db: float) -> None:
        """Handle level updates from the audio thread."""
        self.volume_meter.set_level(db)

    def _update_ui(self) -> None:
        """Update UI elements periodically."""
        state = self.recorder.state
        duration = self.recorder.get_duration()

        # Update duration display
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Update button states
        is_idle = state == RecordingState.IDLE
        is_recording = state == RecordingState.RECORDING
        is_paused = state == RecordingState.PAUSED
        is_stopped = state == RecordingState.STOPPED

        self.record_btn.setEnabled(is_idle)
        self.pause_btn.setEnabled(is_recording or is_paused)
        self.pause_btn.setText("Resume" if is_paused else "Pause")
        self.stop_btn.setEnabled(is_recording or is_paused)
        self.clear_btn.setEnabled(is_recording or is_paused or is_stopped)

        # Show/hide save controls
        self.save_frame.setVisible(is_stopped)

        # Update status
        if is_idle:
            self.status_label.setText("Ready to record")
        elif is_recording:
            self.status_label.setText("Recording...")
        elif is_paused:
            self.status_label.setText("Paused")
        elif is_stopped:
            self.status_label.setText("Recording complete - Save or discard")

    def _on_record(self) -> None:
        """Start recording."""
        self.recorder.start()
        self.volume_meter.reset()

    def _on_pause(self) -> None:
        """Toggle pause/resume."""
        if self.recorder.state == RecordingState.PAUSED:
            self.recorder.resume()
        else:
            self.recorder.pause()

    def _on_stop(self) -> None:
        """Stop recording."""
        self.recorder.stop()

    def _on_clear(self) -> None:
        """Clear the recording."""
        self.recorder.clear()
        self.volume_meter.reset()
        self.duration_label.setText("00:00")

    def _on_save_default(self) -> None:
        """Save to default location."""
        try:
            save_path = self.settings.get_save_path()
            filename = self.recorder.generate_filename()
            filepath = save_path / filename
            saved_path = self.recorder.save(filepath)
            self.status_label.setText(f"Saved: {saved_path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _on_save_custom(self) -> None:
        """Save to custom location."""
        filename = self.recorder.generate_filename() + ".wav"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Voice Note",
            str(Path(self.settings.default_save_path) / filename),
            "WAV Files (*.wav)",
        )
        if filepath:
            try:
                saved_path = self.recorder.save(Path(filepath))
                self.status_label.setText(f"Saved: {saved_path.name}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    def _on_device_changed(self, index: int) -> None:
        """Handle device selection change."""
        if index >= 0 and index < len(self._devices):
            device = self._devices[index]
            self.recorder.set_device(device.index)
            self.settings.preferred_device = device.name
            self.settings.save()

    def _on_browse_path(self) -> None:
        """Browse for default save path."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Save Location",
            self.settings.default_save_path,
        )
        if path:
            self.settings.default_save_path = path
            self.settings.save()
            self.path_edit.setText(path)

    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self.recorder.state != RecordingState.IDLE:
            reply = QMessageBox.question(
                self,
                "Recording in Progress",
                "A recording is in progress. Discard and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        self.recorder.clear()
        event.accept()
