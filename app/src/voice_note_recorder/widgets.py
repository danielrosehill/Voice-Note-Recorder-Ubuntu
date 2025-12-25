"""Custom Qt widgets for the voice note recorder."""

from collections import deque

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient
from PyQt6.QtWidgets import QWidget

from .config import (
    METER_MIN_DB,
    METER_MAX_DB,
    METER_TARGET_MIN_DB,
    METER_TARGET_MAX_DB,
    METER_AVERAGING_SECONDS,
    METER_UPDATE_INTERVAL_MS,
)


class VolumeMeter(QWidget):
    """
    Audio level meter with target range indicators.

    Shows averaged level to reduce jumpiness, with notches indicating
    the recommended recording range.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 40)
        self.setMaximumHeight(50)

        # Level history for averaging
        samples_to_keep = int(
            METER_AVERAGING_SECONDS * 1000 / METER_UPDATE_INTERVAL_MS
        )
        self._level_history: deque[float] = deque(maxlen=samples_to_keep)
        self._current_level_db: float = METER_MIN_DB
        self._display_level_db: float = METER_MIN_DB

        # Colors (light theme)
        self._bg_color = QColor(230, 230, 230)
        self._low_color = QColor(180, 180, 180)
        self._good_color = QColor(76, 175, 80)  # Green
        self._warn_color = QColor(255, 193, 7)  # Amber
        self._peak_color = QColor(244, 67, 54)  # Red
        self._notch_color = QColor(80, 80, 80, 200)

    def set_level(self, db: float) -> None:
        """Update the current level (called from audio callback)."""
        self._current_level_db = max(METER_MIN_DB, min(METER_MAX_DB, db))
        self._level_history.append(self._current_level_db)

        # Calculate weighted average (recent values weighted more)
        if self._level_history:
            weights = list(range(1, len(self._level_history) + 1))
            weighted_sum = sum(w * v for w, v in zip(weights, self._level_history))
            total_weight = sum(weights)
            self._display_level_db = weighted_sum / total_weight

        self.update()

    def reset(self) -> None:
        """Reset the meter."""
        self._level_history.clear()
        self._current_level_db = METER_MIN_DB
        self._display_level_db = METER_MIN_DB
        self.update()

    def _db_to_x(self, db: float, width: int) -> int:
        """Convert dB value to x coordinate."""
        normalized = (db - METER_MIN_DB) / (METER_MAX_DB - METER_MIN_DB)
        return int(normalized * width)

    def paintEvent(self, event) -> None:
        """Paint the volume meter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        margin = 4
        bar_height = height - (margin * 2)

        # Background
        painter.fillRect(0, 0, width, height, self._bg_color)

        # Calculate meter position
        level_x = self._db_to_x(self._display_level_db, width)
        target_min_x = self._db_to_x(METER_TARGET_MIN_DB, width)
        target_max_x = self._db_to_x(METER_TARGET_MAX_DB, width)

        # Draw meter bar with gradient
        if level_x > 0:
            gradient = QLinearGradient(0, 0, width, 0)
            gradient.setColorAt(0, self._low_color)
            gradient.setColorAt(target_min_x / width, self._good_color)
            gradient.setColorAt(target_max_x / width, self._warn_color)
            gradient.setColorAt(1, self._peak_color)

            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(margin, margin, level_x - margin, bar_height)

        # Draw unfilled portion
        painter.setBrush(QColor(200, 200, 200))
        if level_x < width - margin:
            painter.drawRect(level_x, margin, width - level_x - margin, bar_height)

        # Draw target range notches
        pen = QPen(self._notch_color)
        pen.setWidth(2)
        painter.setPen(pen)

        # Min target notch
        painter.drawLine(target_min_x, 0, target_min_x, height)
        # Max target notch
        painter.drawLine(target_max_x, 0, target_max_x, height)

        # Draw dB labels
        painter.setPen(QColor(100, 100, 100))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # Label at target positions
        painter.drawText(target_min_x - 15, height - 2, f"{METER_TARGET_MIN_DB}")
        painter.drawText(target_max_x - 15, height - 2, f"{METER_TARGET_MAX_DB}")

        painter.end()
