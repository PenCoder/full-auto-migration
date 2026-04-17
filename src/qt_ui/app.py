from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.config import MigrationConfigRoot
from src.qt_ui.main_window import QtMigrationWindow


def run_qt_app(config: MigrationConfigRoot, runtime_mode: str) -> int:
    app = QApplication(sys.argv)
    qss_path = Path(__file__).resolve().parent / "theme.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    window = QtMigrationWindow(config=config, runtime_mode=runtime_mode)
    window.show()
    return app.exec()
