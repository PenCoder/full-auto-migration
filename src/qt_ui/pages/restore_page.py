"""Restore page for replaying a migration bundle on Linux."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class RestorePage(BasePage):
    """Restore a selected bundle and report progress back to the user."""

    def __init__(self, ui_state, run_restore_cb: Callable[[Path], dict]) -> None:
        super().__init__(ui_state)
        self.run_restore_cb = run_restore_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.bundle_path: Path | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🚀",
            "Welcome to Linux — let's bring your data over!",
            "Point us to the migration bundle you created on Windows "
            "and we'll restore your files and app list automatically.",
        ))

        info = self.create_trust_banner(
            "✅  Nothing is overwritten without your confirmation. "
            "Your bundle contains only copies — your Windows files are still safe."
        )
        root.addWidget(info)

        row = QHBoxLayout()
        self.bundle_edit = QLineEdit()
        self.bundle_edit.setReadOnly(True)
        self.bundle_edit.setPlaceholderText("Click 'Browse' to find your migration bundle folder")
        row.addWidget(self.bundle_edit)
        browse = QPushButton("Browse")
        browse.setProperty("role", "primary")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        root.addLayout(row)

        self.status = QLabel("Select the migration bundle folder you copied from your Windows machine, then click Start.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.restore_btn = QPushButton("Restore My Files to This Computer")
        self.restore_btn.setProperty("role", "primary")
        self.restore_btn.setMinimumHeight(48)
        self.restore_btn.setFixedWidth(280)
        self.restore_btn.clicked.connect(self._run_restore)
        root.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
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
        self.status.setText("Restoring your files — this may take a few minutes depending on how much data you have...")
        worker = FunctionWorker(self.run_restore_cb, self.bundle_path)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.restore_completed = True
            self.status.setText(
                "🎉  Your files have been restored! Everything from your Windows machine is now on Linux. "
                "Click Continue to verify that everything arrived safely."
            )
        else:
            self.status.setText("Restore complete — click Continue to check everything arrived correctly.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Restore failed.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.restore_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        self.restore_btn.setEnabled(self.bundle_path is not None)
        self.next_btn.setEnabled(self.ui_state.restore_completed or self.ui_state.mode == "expert")
        mode = self.ui_state.mode
        if not self.ui_state.restore_completed:
            if mode == "guided":
                self.status.setText(
                    "Browse to the migration bundle you saved from your Windows machine, then click Restore."
                )
            elif mode == "balanced":
                self.status.setText(
                    "Select your migration bundle folder, then click Restore. "
                    "Check the Expert panel for advanced restore options."
                )
