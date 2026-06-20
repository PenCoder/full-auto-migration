"""Backup bundle page — user starts the backup manually and can cancel mid-run."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.services.migration_service import BUNDLE_ARCHIVE_NAME
from src.qt_ui.utils.usb_utils import copy_bundle_to_usb, detect_usb_drives
from src.qt_ui.workers import FunctionWorker

_NO_USB_LABEL = "— Save on this computer only —"


class BackupBundlePage(BasePage):
    """Create the migration backup bundle and its manifest."""

    def __init__(self, ui_state, run_backup_cb: Callable[..., dict | None]) -> None:
        super().__init__(ui_state)
        self.run_backup_cb = run_backup_cb
        self.thread_pool = QThreadPool.globalInstance()
        self._detected_drives: list[dict] = []
        self._cancel_event: threading.Event | None = None
        self._build_ui()
        self.refresh()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "📦",
            "Packing your migration bundle",
            "Your files, app list, and settings are packed into one portable folder "
            "you can carry across to your new Linux computer.",
        ))

        root.addWidget(self.create_trust_banner(
            "Your original files stay untouched on this Windows machine. "
            "The bundle is a safe copy — nothing is deleted or moved."
        ))

        root.addWidget(self._build_usb_section())

        self.status = QLabel("Ready to create your migration bundle.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.success_banner, self.success_label = self.create_success_banner("")
        self.success_banner.setVisible(False)
        root.addWidget(self.success_banner)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        self.backup_btn = QPushButton("Create Backup Bundle")
        self.backup_btn.setProperty("role", "cta")
        self.backup_btn.setMinimumHeight(44)
        self.backup_btn.setMinimumWidth(220)
        self.backup_btn.clicked.connect(self._run_backup)
        btn_row.addWidget(self.backup_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(44)
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

    def _build_usb_section(self) -> QWidget:
        box = QFrame()
        box.setObjectName("InfoPanel")
        box.setStyleSheet(
            "QFrame#InfoPanel { background-color: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 6px; }"
            " QLabel { background: transparent; border: none; }"
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        icon = QLabel("💾")
        icon.setStyleSheet("font-size: 16px;")
        title = QLabel("Save bundle to a USB drive (optional)")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        self.usb_combo = QComboBox()
        self.usb_combo.setMinimumWidth(320)
        self.usb_combo.addItem(_NO_USB_LABEL)
        self.usb_combo.currentIndexChanged.connect(self._on_usb_selection_changed)
        picker_row.addWidget(self.usb_combo, stretch=1)

        self.refresh_usb_btn = QPushButton("Refresh")
        self.refresh_usb_btn.setProperty("role", "badge")
        self.refresh_usb_btn.setMinimumWidth(80)
        self.refresh_usb_btn.clicked.connect(self._detect_usb_drives)
        picker_row.addWidget(self.refresh_usb_btn)

        self.browse_usb_btn = QPushButton("Browse…")
        self.browse_usb_btn.setProperty("role", "badge")
        self.browse_usb_btn.setMinimumWidth(80)
        self.browse_usb_btn.clicked.connect(self._browse_usb)
        picker_row.addWidget(self.browse_usb_btn)

        layout.addLayout(picker_row)

        self.usb_dest_label = QLabel("")
        self.usb_dest_label.setStyleSheet("font-size: 13px; color: #6B7280;")
        self.usb_dest_label.setWordWrap(True)
        self.usb_dest_label.setVisible(False)
        layout.addWidget(self.usb_dest_label)

        return box

    # ── USB detection & selection ────────────────────────────────────────────

    def _detect_usb_drives(self) -> None:
        self._detected_drives = detect_usb_drives()
        current_path = self.ui_state.backup_usb_path

        self.usb_combo.blockSignals(True)
        self.usb_combo.clear()
        self.usb_combo.addItem(_NO_USB_LABEL)
        for drive in self._detected_drives:
            self.usb_combo.addItem(drive["display"], userData=drive["path"])

        # Restore previous selection if the drive is still present
        if current_path:
            for i in range(1, self.usb_combo.count()):
                if self.usb_combo.itemData(i) == current_path:
                    self.usb_combo.setCurrentIndex(i)
                    break
            else:
                # Previously chosen path no longer in detected list — keep it as custom
                self.usb_combo.addItem(f"Custom: {current_path}", userData=current_path)
                self.usb_combo.setCurrentIndex(self.usb_combo.count() - 1)

        self.usb_combo.blockSignals(False)
        self._on_usb_selection_changed(self.usb_combo.currentIndex())

        if not self._detected_drives:
            self.usb_dest_label.setText(
                "No USB drives detected. Insert a drive and click Refresh, or use Browse to pick any folder."
            )
            self.usb_dest_label.setVisible(True)

    def _on_usb_selection_changed(self, index: int) -> None:
        if index == 0:
            self.ui_state.backup_usb_path = ""
            self.usb_dest_label.setVisible(False)
        else:
            path = self.usb_combo.itemData(index) or ""
            self.ui_state.backup_usb_path = path
            dest = Path(path) / BUNDLE_ARCHIVE_NAME
            self.usb_dest_label.setText(f"Bundle archive will be copied to: {dest}")
            self.usb_dest_label.setVisible(True)

    def _browse_usb(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select USB Drive or Destination Folder")
        if not folder:
            return
        self.ui_state.backup_usb_path = folder
        # Add as a custom entry and select it
        self.usb_combo.blockSignals(True)
        # Remove any previous "Custom:" entry
        for i in range(self.usb_combo.count() - 1, 0, -1):
            if self.usb_combo.itemText(i).startswith("Custom:"):
                self.usb_combo.removeItem(i)
        self.usb_combo.addItem(f"Custom: {folder}", userData=folder)
        self.usb_combo.setCurrentIndex(self.usb_combo.count() - 1)
        self.usb_combo.blockSignals(False)
        self._on_usb_selection_changed(self.usb_combo.currentIndex())

    # ── Page entry ───────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._detect_usb_drives()

    # ── Success banner ───────────────────────────────────────────────────────

    def _set_success(self, message: str) -> None:
        self.success_label.setText(message)
        self.success_banner.setVisible(True)
        self.status.setVisible(False)

    def _clear_success(self) -> None:
        self.success_banner.setVisible(False)
        self.status.setVisible(True)

    # ── Backup ───────────────────────────────────────────────────────────────

    def _run_backup(self) -> None:
        if self.is_processing:
            return
        self._clear_success()
        self._cancel_event = threading.Event()
        self.set_scanning(True)
        self.backup_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(True)
        self.status.setText(
            "Creating your backup bundle — copying files and building the archive…"
        )
        worker = FunctionWorker(self.run_backup_cb, self._cancel_event)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_cancel_clicked(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.cancel_btn.setEnabled(False)
        self.status.setText("Cancelling — finishing the current file…")

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict) and result.get("cancelled"):
            self._clear_success()
            self.status.setText("Backup cancelled. Click 'Create Backup Bundle' to try again.")
        elif isinstance(result, dict):
            self.ui_state.backup_completed = True
            self.ui_state.bundle_archive_path = result.get("bundle_archive_path", "")
            total = int(result.get("total_files", 0))
            usb_path = self.ui_state.backup_usb_path
            if usb_path and self.ui_state.bundle_archive_path:
                self.status.setText(
                    f"Bundle ready — {total} file{'s' if total != 1 else ''} packed."
                )
                self._copy_to_usb(usb_path)
                return
            else:
                self._set_success(
                    f"Bundle ready — {total} file{'s' if total != 1 else ''} packed into "
                    f"{Path(self.ui_state.bundle_archive_path).name or 'migration_bundle.zip'}. "
                    "Copy that file to your Linux machine and click 'Continue'."
                )
        else:
            self.ui_state.backup_completed = True
            self._set_success("Bundle created — ready to move to Linux!")
        self.refresh()

    def _copy_to_usb(self, usb_path: str) -> None:
        self.status.setText(f"Copying bundle to {usb_path} — please wait…")
        self.set_scanning(True)
        archive_path = Path(self.ui_state.bundle_archive_path)
        worker = FunctionWorker(copy_bundle_to_usb, archive_path, usb_path)
        worker.signals.result.connect(self._on_usb_copy_result)
        worker.signals.error.connect(self._on_usb_copy_error)
        worker.signals.finished.connect(self._on_usb_copy_finished)
        self.thread_pool.start(worker)

    def _on_usb_copy_result(self, dest: object) -> None:
        self._set_success(
            f"Bundle saved to {dest} — eject the USB drive and carry it to your Linux machine, then click 'Continue'."
        )
        self.refresh()

    def _on_usb_copy_error(self, error: str) -> None:
        self._clear_success()
        self.status.setText(
            f"Bundle created, but USB copy failed: {user_facing_error(error)}\n"
            "You can copy the bundle archive manually from your computer."
        )
        self.refresh()

    def _on_usb_copy_finished(self) -> None:
        self.set_scanning(False)
        self.backup_btn.setEnabled(True)
        self.refresh()

    def _on_error(self, error: str) -> None:
        self._clear_success()
        self.ui_state.last_error = error
        self.status.setText(f"Backup failed. {user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self._cancel_event = None
        self.set_scanning(False)
        self.backup_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.refresh()

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        mode = self.ui_state.mode
        done = self.ui_state.backup_completed

        self.backup_btn.setVisible(True)
        if mode == "guided":
            self.backup_btn.setText("Re-run Bundle Creation" if done else "Create Backup Bundle")
            if not done and not self.is_processing:
                self.status.setText(
                    "Your files, app list, and desktop settings are ready to pack. "
                    "Click 'Create Backup Bundle' to start."
                )
        elif mode == "balanced":
            self.backup_btn.setText("Re-run Bundle Creation" if done else "Create My Migration Bundle")
            if not done and not self.is_processing:
                self.status.setText(
                    "Your file and app selections from earlier steps are ready. "
                    "Click 'Create My Migration Bundle' to start."
                )
        else:
            self.backup_btn.setText("Re-run Bundle Creation" if done else "Create Migration Bundle")
            if not done and not self.is_processing:
                self.status.setText(
                    "Your custom app mappings, file selections, and settings are ready. "
                    "Click 'Create Migration Bundle' to start."
                )

    def can_proceed(self) -> bool:
        return self.ui_state.backup_completed or self.ui_state.mode == "expert"

    def blocked_reason(self) -> str:
        return "Create your migration bundle before continuing."

