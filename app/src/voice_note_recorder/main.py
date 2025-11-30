"""Main entry point for the Voice Note Recorder application."""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .ui import MainWindow


def main():
    """Run the application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Voice Note Recorder")
    app.setOrganizationName("DanielRosehill")
    app.setApplicationVersion("0.1.0")

    # Set application-wide style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
