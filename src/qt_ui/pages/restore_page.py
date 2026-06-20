"""Restore page for replaying a migration bundle on Linux."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.constants import DATA_DIR
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
        # When True, refresh() leaves self.status alone — set whenever a
        # restore attempt just finished (success, warnings, or failure) so
        # that result doesn't get silently overwritten by generic guidance
        # text the next time refresh() runs (e.g. from _on_finished).
        self._sticky_status = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🚀",
            "Welcome to Linux — restore your data",
            "Point to the migration bundle you created on Windows "
            "and your files and app list will be restored automatically.",
        ))

        info = self.create_trust_banner(
            "Nothing is overwritten without your confirmation. "
            "Your bundle contains only copies — your Windows files are still safe."
        )
        root.addWidget(info)

        bundle_card = QFrame()
        bundle_card.setProperty("card", "section")
        bundle_card_layout = QVBoxLayout(bundle_card)
        bundle_card_layout.setContentsMargins(14, 12, 14, 12)
        bundle_card_layout.setSpacing(8)

        bundle_title = QLabel("Migration bundle location")
        bundle_title.setObjectName("SectionTitle")
        bundle_card_layout.addWidget(bundle_title)

        row = QHBoxLayout()
        self.bundle_edit = QLineEdit()
        self.bundle_edit.setReadOnly(True)
        self.bundle_edit.setPlaceholderText("Click 'Browse' to select the migration_bundle.zip (or an already-unzipped bundle folder)")
        row.addWidget(self.bundle_edit)
        browse = QPushButton("Browse")
        browse.setProperty("role", "badge")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        bundle_card_layout.addLayout(row)

        root.addWidget(bundle_card)

        self.status = QLabel("Select the migration bundle (.zip) you copied from your Windows machine, then click Start.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.restore_btn = QPushButton("Restore My Files to This Computer")
        self.restore_btn.setProperty("role", "cta")
        self.restore_btn.setMinimumHeight(48)
        self.restore_btn.setMinimumWidth(280)
        self.restore_btn.clicked.connect(self._run_restore)
        root.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)

    def _browse(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select migration_bundle.zip — or any file inside an already-unzipped bundle folder",
            "",
            "Migration bundle (*.zip);;Bundle manifest (manifest.json);;All files (*)",
        )
        if not selected:
            return

        selected_path = Path(selected)
        if selected_path.suffix.lower() == ".zip":
            extract_dir = DATA_DIR / "imported_bundle"
            try:
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                extract_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(selected_path) as zf:
                    zf.extractall(extract_dir)
            except Exception as exc:
                self.status.setText(f"Could not extract bundle archive: {user_facing_error(str(exc))}")
                self._sticky_status = True
                return
            self.bundle_path = extract_dir
            self.status.setText(f"Bundle archive '{selected_path.name}' extracted — ready to restore.")
        else:
            # User pointed at a file inside an already-unzipped bundle folder
            # (e.g. manifest.json) — use its parent folder as the bundle root.
            self.bundle_path = selected_path.parent
            self.status.setText(f"Bundle folder selected: {self.bundle_path}")

        self._sticky_status = True
        self.bundle_edit.setText(str(self.bundle_path))
        self.refresh()

    def _run_restore(self) -> None:
        if not self.bundle_path:
            self.status.setText("Please select a backup bundle archive or folder first.")
            return
        if self.is_processing:
            return

        self.set_scanning(True)
        self.restore_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Restoring your files — this may take a few minutes depending on how much data you have...")
        worker = FunctionWorker(self.run_restore_cb, self.bundle_path)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        self._sticky_status = True
        if isinstance(result, dict):
            self.ui_state.restore_completed = True
            warnings = result.get("warnings") or []
            if warnings:
                self.status.setText(
                    "✅  Your files have been restored, but a few optional steps couldn't complete:\n"
                    + "\n".join(f"• {w}" for w in warnings)
                    + "\nClick Continue to verify what arrived safely."
                )
            else:
                self.status.setText(
                    "🎉  Your files have been restored! Everything from your Windows machine is now on Linux. "
                    "Click Continue to verify that everything arrived safely."
                )
        else:
            self.status.setText("Restore complete — click Continue to check everything arrived correctly.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self._sticky_status = True
        self.ui_state.last_error = error
        self.status.setText(f"Restore failed.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.set_scanning(False)
        self.restore_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def can_proceed(self) -> bool:
        return self.ui_state.restore_completed or self.ui_state.mode == "expert"

    def blocked_reason(self) -> str:
        return "Restore your files before continuing."

    def refresh(self) -> None:
        self.restore_btn.setEnabled(self.bundle_path is not None)
        mode = self.ui_state.mode
        # Once _browse()/_on_result()/_on_error() have set an explicit,
        # meaningful status message, leave it alone — don't let a later
        # refresh() call (e.g. from _on_finished) silently overwrite it
        # with generic guidance text.
        if self._sticky_status:
            return
        if not self.ui_state.restore_completed and not self.is_processing:
            if self.bundle_path is not None:
                self.status.setText("Bundle selected — click Restore to begin.")
            elif mode == "guided":
                self.status.setText(
                    "Browse to the migration bundle you saved from your Windows machine, then click Restore."
                )
            elif mode == "balanced":
                self.status.setText(
                    "Select your migration bundle (.zip), then click Restore. "
                    "Check the Expert panel for advanced restore options."
                )
