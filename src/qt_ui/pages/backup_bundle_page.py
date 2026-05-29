"""Backup bundle page — auto-triggers on first entry, button available for re-runs."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtWidgets import QLabel, QPushButton

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
            "Packing your migration bundle",
            "We're putting your files, app list, and settings into one portable bundle "
            "you can carry across to your new Linux computer.",
        ))

        root.addWidget(self.create_trust_banner(
            "✅  Your original files stay untouched on this Windows machine. "
            "The bundle is a safe copy — nothing is deleted or moved."
        ))

        self.status = QLabel("Preparing your migration bundle…")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.backup_btn = QPushButton("Create Backup Bundle")
        self.backup_btn.setProperty("role", "badge")
        self.backup_btn.setMinimumHeight(44)
        self.backup_btn.setFixedWidth(220)
        self.backup_btn.clicked.connect(self._run_backup)
        root.addWidget(self.backup_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Continue to Linux Restore")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(220)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    # ── Auto-trigger ─────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.ui_state.backup_completed and not self.is_processing:
            QTimer.singleShot(300, self._run_backup)

    # ── Backup ───────────────────────────────────────────────────────────────

    def _run_backup(self) -> None:
        if self.is_processing:
            return
        self.set_scanning(True)
        self.backup_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.status.setText(
            "Creating your backup bundle — copying files and building the archive…"
        )
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
                f"🎉  Bundle ready — {total} file{'s' if total != 1 else ''} packed. "
                "Copy the bundle folder to your Linux machine and click 'Continue'."
            )
        else:
            self.status.setText("Bundle created — you're ready to move to Linux!")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Backup failed. {user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.set_scanning(False)
        self.backup_btn.setEnabled(True)
        self.refresh()

    def refresh(self) -> None:
        mode = self.ui_state.mode
        done = self.ui_state.backup_completed

        if mode == "guided":
            self.backup_btn.setVisible(done)
            self.backup_btn.setText("Re-run Bundle Creation")
            if not done and not self.is_processing:
                self.status.setText(
                    "Building your migration bundle automatically — "
                    "your files, app list, and desktop settings are all included."
                )
        elif mode == "balanced":
            self.backup_btn.setVisible(True)
            self.backup_btn.setText("Re-run Bundle Creation" if done else "Create My Migration Bundle")
            if not done and not self.is_processing:
                self.status.setText(
                    "Your file and app selections from earlier steps are included in this bundle."
                )
        else:
            self.backup_btn.setVisible(True)
            self.backup_btn.setText("Re-run Bundle Creation" if done else "Create Migration Bundle")
            if not done and not self.is_processing:
                self.status.setText(
                    "Your custom app mappings, file selections, and settings are all included."
                )

        self.next_btn.setEnabled(done or mode == "expert")
