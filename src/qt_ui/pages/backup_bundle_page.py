"""Backup bundle page for packaging migration artifacts."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class BackupBundlePage(BasePage):
    """Create the migration backup bundle and its manifest."""

    def __init__(self, ui_state, run_backup_cb: Callable[[], dict | None]) -> None:
        super().__init__(ui_state)
        self.run_backup_cb = run_backup_cb
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "📦",
            "Pack everything up and go!",
            "We'll put your files, app list, and settings into one neat, portable bundle "
            "that you can carry across to your new Linux computer.",
        ))

        info = self.create_trust_banner(
            "✅  Your original files stay untouched on this Windows machine. "
            "The bundle is a safe copy — nothing here is deleted or moved."
        )
        root.addWidget(info)

        self.status = QLabel("Ready to create your migration bundle. Click the button below to start.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.backup_btn = QPushButton("Create Backup Bundle")
        self.backup_btn.setProperty("role", "primary")
        self.backup_btn.setMinimumHeight(48)
        self.backup_btn.setFixedWidth(250)
        self.backup_btn.clicked.connect(self._run_backup)
        root.addWidget(self.backup_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_backup(self) -> None:
        self.backup_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Creating backup bundle and optional archive...")
        worker = FunctionWorker(self.run_backup_cb)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.backup_completed = True
            total = int(result.get("total_files", 0))
            self.status.setText(
                f"🎉  Your migration bundle is ready! It contains {total} file{'s' if total != 1 else ''}. "
                "You can now copy this bundle to your Linux computer and run the restore step."
            )
        else:
            self.status.setText("Bundle created — you're ready to move to Linux!")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Backup failed.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.backup_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided":
            if not self.ui_state.backup_completed:
                self.status.setText(
                    "We'll pack up everything you need in one click — your files, app list, and desktop settings."
                )
            self.backup_btn.setText("Create My Migration Bundle")
        elif mode == "balanced":
            if not self.ui_state.backup_completed:
                self.status.setText(
                    "Your file and app selections from earlier steps are included in this bundle."
                )
            self.backup_btn.setText("Create My Migration Bundle")
        else:
            if not self.ui_state.backup_completed:
                self.status.setText(
                    "Your custom app mappings, file selections, and settings are all included in this bundle."
                )
            self.backup_btn.setText("Create Migration Bundle")

        self.next_btn.setEnabled(self.ui_state.backup_completed or self.ui_state.mode == "expert")
