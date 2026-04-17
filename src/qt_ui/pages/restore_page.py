from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QVBoxLayout

from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class RestorePage(BasePage):
    def __init__(self, ui_state, run_restore_cb: Callable[[Path], dict]) -> None:
        super().__init__(ui_state)
        self.run_restore_cb = run_restore_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.bundle_path: Path | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        step = QLabel("Migration - Step 1 of 2: Restore Data on Linux")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(50)
        self.step_progress.setTextVisible(False)
        self.step_progress.setFixedHeight(10)
        root.addWidget(self.step_progress)

        text = QLabel("Welcome to Linux! Select your backup bundle to begin the restore.")
        text.setObjectName("HeroTitle")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        root.addWidget(text)

        row = QHBoxLayout()
        self.bundle_edit = QLineEdit()
        self.bundle_edit.setReadOnly(True)
        self.bundle_edit.setPlaceholderText("Select backup bundle directory")
        row.addWidget(self.bundle_edit)
        browse = QPushButton("Browse")
        browse.setProperty("role", "primary")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        root.addLayout(row)

        self.status = QLabel("Choose a folder containing manifest.json and backup.zip.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.restore_btn = QPushButton("Start Restore")
        self.restore_btn.setProperty("role", "primary")
        self.restore_btn.setMinimumHeight(58)
        self.restore_btn.setFixedWidth(260)
        self.restore_btn.clicked.connect(self._run_restore)
        root.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(220)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Backup Bundle Folder")
        if selected:
            self.bundle_path = Path(selected)
            self.bundle_edit.setText(str(self.bundle_path))
            self.refresh()

    def _run_restore(self) -> None:
        if not self.bundle_path:
            self.status.setText("Please select a backup bundle folder first.")
            return

        self.restore_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Restoring files and installing selected applications...")
        worker = FunctionWorker(self.run_restore_cb, self.bundle_path)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        if result:
            self.ui_state.restore_completed = True
            self.status.setText("Restore completed successfully.")
        else:
            self.status.setText("Restore finished without a result.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Restore failed: {error}")
        self.refresh()

    def _on_finished(self) -> None:
        self.restore_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        self.restore_btn.setEnabled(self.bundle_path is not None)
        self.next_btn.setEnabled(self.ui_state.restore_completed or self.ui_state.mode == "expert")
