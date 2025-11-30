"""Main UI window for the voice note recorder."""

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction, QShortcut, QKeySequence
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
    QTabWidget,
    QTextBrowser,
)

from .audio import AudioRecorder, RecordingState
from .config import (
    Settings,
    METER_UPDATE_INTERVAL_MS,
    GEMINI_MAX_FILE_SIZE_MB,
    QualityPreset,
    QUALITY_PRESETS,
)
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
            level_callback=lambda db: self._level_signal.level_changed.emit(db),
            quality_settings=self.settings.get_quality_settings(),
        )

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_timer()
        self._load_devices()
        self._apply_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Voice Note Recorder")
        self.setMinimumSize(420, 420)
        self.setMaximumSize(520, 520)

        # Central widget with tab container
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create tabs
        self._setup_record_tab()
        self._setup_settings_tab()
        self._setup_about_tab()

        # Apply dark theme
        self._apply_theme()

    def _setup_record_tab(self) -> None:
        """Set up the main recording tab."""
        record_widget = QWidget()
        layout = QVBoxLayout(record_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Volume meter
        self.volume_meter = VolumeMeter()
        layout.addWidget(self.volume_meter)

        # Duration and file size display
        time_info_layout = QHBoxLayout()

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
        time_info_layout.addWidget(self.duration_label)

        # File size estimate
        self.size_label = QLabel("0.0 MB")
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-family: monospace;
                color: #888;
            }
        """)
        time_info_layout.addWidget(self.size_label)

        layout.addLayout(time_info_layout)

        # Max duration indicator (dynamic based on quality)
        self.max_duration_label = QLabel("")
        self.max_duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.max_duration_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.max_duration_label)
        self._update_max_duration_label()

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

        self.save_default_btn = QPushButton("Save to Default (Ctrl+S)")
        self.save_default_btn.setMinimumHeight(36)
        self.save_default_btn.clicked.connect(self._on_save_default)
        self.save_default_btn.setStyleSheet(self._button_style("#2196F3", "#1976D2"))
        save_layout.addWidget(self.save_default_btn)

        self.save_custom_btn = QPushButton("Save to Custom... (Ctrl+Shift+S)")
        self.save_custom_btn.setMinimumHeight(36)
        self.save_custom_btn.clicked.connect(self._on_save_custom)
        self.save_custom_btn.setStyleSheet(self._button_style("#607D8B", "#546E7A"))
        save_layout.addWidget(self.save_custom_btn)

        self.save_frame.hide()
        layout.addWidget(self.save_frame)

        layout.addStretch()
        self.tabs.addTab(record_widget, "Record")

    def _setup_settings_tab(self) -> None:
        """Set up the settings tab."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Quality preset selection
        quality_group_label = QLabel("Recording Quality")
        quality_group_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 13px;")
        layout.addWidget(quality_group_label)

        quality_layout = QHBoxLayout()
        quality_label = QLabel("Preset:")
        quality_label.setStyleSheet("color: #aaa;")
        quality_layout.addWidget(quality_label)

        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumWidth(200)
        for preset in QualityPreset:
            settings = QUALITY_PRESETS[preset]
            self.quality_combo.addItem(
                f"{settings.name} ({settings.max_duration_str})",
                preset.value
            )
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_combo, 1)
        layout.addLayout(quality_layout)

        # Quality description
        self.quality_desc_label = QLabel("")
        self.quality_desc_label.setStyleSheet("color: #888; font-size: 11px; margin-left: 60px;")
        self.quality_desc_label.setWordWrap(True)
        layout.addWidget(self.quality_desc_label)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("background-color: #444;")
        layout.addWidget(separator1)

        # Device selection
        device_group_label = QLabel("Audio Input")
        device_group_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 13px;")
        layout.addWidget(device_group_label)

        device_layout = QHBoxLayout()
        device_label = QLabel("Microphone:")
        device_label.setStyleSheet("color: #aaa;")
        device_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self.device_combo, 1)
        layout.addLayout(device_layout)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #444;")
        layout.addWidget(separator2)

        # Save path
        path_group_label = QLabel("Default Save Location")
        path_group_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 13px;")
        layout.addWidget(path_group_label)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_path)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)

        layout.addStretch()
        self.tabs.addTab(settings_widget, "Settings")

    def _setup_about_tab(self) -> None:
        """Set up the About tab with quality preset explanations."""
        about_widget = QWidget()
        layout = QVBoxLayout(about_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        about_text = QTextBrowser()
        about_text.setOpenExternalLinks(True)
        about_text.setStyleSheet("""
            QTextBrowser {
                background-color: #252525;
                color: #e0e0e0;
                border: none;
                font-size: 12px;
            }
        """)

        about_html = f"""
        <h3 style="color: #4CAF50;">Voice Note Recorder</h3>
        <p>A lightweight voice recorder optimized for AI transcription services
        like Google Gemini and OpenAI Whisper.</p>

        <h4 style="color: #2196F3;">Quality Presets</h4>
        <p>All presets output mono WAV files optimized for speech-to-text.
        Choose based on your recording length needs:</p>

        <table style="margin-left: 10px;">
        <tr>
            <td style="color: #4CAF50; font-weight: bold; padding: 8px 12px 8px 0;">Standard</td>
            <td style="padding: 8px 0;">
                <b>16 kHz, 16-bit</b> &mdash; ~11 min per {GEMINI_MAX_FILE_SIZE_MB} MB<br/>
                <span style="color: #888;">Best clarity. Native format for Gemini/Whisper.
                Use for important notes where quality matters.</span>
            </td>
        </tr>
        <tr>
            <td style="color: #FF9800; font-weight: bold; padding: 8px 12px 8px 0;">Extended</td>
            <td style="padding: 8px 0;">
                <b>8 kHz, 16-bit</b> &mdash; ~22 min per {GEMINI_MAX_FILE_SIZE_MB} MB<br/>
                <span style="color: #888;">Good quality for longer recordings.
                Still very clear for speech. <b>Recommended default.</b></span>
            </td>
        </tr>
        <tr>
            <td style="color: #f44336; font-weight: bold; padding: 8px 12px 8px 0;">Maximum Duration</td>
            <td style="padding: 8px 0;">
                <b>8 kHz, 8-bit</b> &mdash; ~44 min per {GEMINI_MAX_FILE_SIZE_MB} MB<br/>
                <span style="color: #888;">Telephone quality. Use for very long voice notes
                like meeting recordings or brainstorming sessions.</span>
            </td>
        </tr>
        </table>

        <h4 style="color: #2196F3; margin-top: 16px;">API Limits</h4>
        <p>Gemini's file upload limit is <b>{GEMINI_MAX_FILE_SIZE_MB} MB</b>.
        The max duration shown accounts for this limit.
        For longer recordings, consider splitting into multiple files.</p>

        <p style="color: #666; margin-top: 20px; font-size: 11px;">
        Built with PyQt6 and sounddevice.
        </p>
        """

        about_text.setHtml(about_html)
        layout.addWidget(about_text)

        self.tabs.addTab(about_widget, "About")

    def _update_max_duration_label(self) -> None:
        """Update the max duration label based on current quality settings."""
        quality = self.recorder.quality
        max_secs = quality.max_duration_seconds
        max_mins = max_secs // 60
        max_secs_remainder = max_secs % 60
        self.max_duration_label.setText(
            f"Max: {max_mins}:{max_secs_remainder:02d} ({GEMINI_MAX_FILE_SIZE_MB} MB) - {quality.name}"
        )

    def _update_quality_description(self) -> None:
        """Update the quality description label."""
        preset = self.settings.get_quality_preset()
        settings = QUALITY_PRESETS[preset]
        self.quality_desc_label.setText(settings.description)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Save to default (Ctrl+S) - only active when save frame is visible
        self.save_default_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_default_shortcut.activated.connect(self._on_shortcut_save_default)

        # Save to custom (Ctrl+Shift+S)
        self.save_custom_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.save_custom_shortcut.activated.connect(self._on_shortcut_save_custom)

    def _on_shortcut_save_default(self) -> None:
        """Handle Ctrl+S shortcut."""
        if self.save_frame.isVisible():
            self._on_save_default()

    def _on_shortcut_save_custom(self) -> None:
        """Handle Ctrl+Shift+S shortcut."""
        if self.save_frame.isVisible():
            self._on_save_custom()

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
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #aaa;
                padding: 8px 16px;
                border: 1px solid #444;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border-bottom: 1px solid #1e1e1e;
            }
            QTabBar::tab:hover:!selected {
                background-color: #383838;
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

        # Select quality preset
        self.quality_combo.blockSignals(True)
        current_preset = self.settings.get_quality_preset()
        for i, preset in enumerate(QualityPreset):
            if preset == current_preset:
                self.quality_combo.setCurrentIndex(i)
                break
        self.quality_combo.blockSignals(False)
        self._update_quality_description()

    def _on_level_update(self, db: float) -> None:
        """Handle level updates from the audio thread."""
        self.volume_meter.set_level(db)

    def _update_ui(self) -> None:
        """Update UI elements periodically."""
        state = self.recorder.state
        duration = self.recorder.get_duration()
        quality = self.recorder.quality

        # Update duration display
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Update file size estimate (using current quality's bytes per second)
        file_size_bytes = duration * quality.bytes_per_second
        file_size_mb = file_size_bytes / (1024 * 1024)
        self.size_label.setText(f"{file_size_mb:.1f} MB")

        # Warn if approaching Gemini limit (based on current quality's max duration)
        max_duration = quality.max_duration_seconds
        if duration > max_duration * 0.9:
            self.size_label.setStyleSheet("font-size: 14px; font-family: monospace; color: #f44336;")
        elif duration > max_duration * 0.75:
            self.size_label.setStyleSheet("font-size: 14px; font-family: monospace; color: #FF9800;")
        else:
            self.size_label.setStyleSheet("font-size: 14px; font-family: monospace; color: #888;")

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

        # Disable quality changes while recording
        self.quality_combo.setEnabled(is_idle)

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
        self.size_label.setText("0.0 MB")
        self.size_label.setStyleSheet("font-size: 14px; font-family: monospace; color: #888;")

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

    def _on_quality_changed(self, index: int) -> None:
        """Handle quality preset selection change."""
        presets = list(QualityPreset)
        if 0 <= index < len(presets):
            preset = presets[index]
            quality_settings = QUALITY_PRESETS[preset]

            # Update recorder
            self.recorder.set_quality(quality_settings)

            # Save preference
            self.settings.quality_preset = preset.value
            self.settings.save()

            # Update UI elements
            self._update_quality_description()
            self._update_max_duration_label()

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
