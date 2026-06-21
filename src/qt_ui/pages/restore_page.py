"""Single-window Linux-side page: restore, verify, and report — no step navigation.

Replaces the old three-page Restore → Validation → Final Report flow. The
user browses to a bundle, clicks one button, and the page chains restore →
verify → report generation automatically, ending with the report shown
inline. If a phase fails, the user picks Restart (full reset) or Review &
Complete Anyway (continue past the failed phase with whatever succeeded).
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.constants import DATA_DIR, FINAL_REPORT_HTML, FINAL_REPORT_JSON, FINAL_REPORT_MARKDOWN, RESTORE_REPORT
from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class _BundlePickerDialog(QFileDialog):
    """File dialog that accepts either a folder or a .zip file as the result.

    A plain QFileDialog can only ever do one or the other — picking the
    bundle *folder* itself (rather than a file inside it) would just
    navigate into it instead of selecting it. Qt's native dialog can't be
    coaxed into mixed mode, so this runs Qt's own cross-platform dialog
    and overrides accept() to also treat a selected directory as valid.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent, "Select your migration bundle — the unzipped folder, or the migration_bundle.zip file")
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.setNameFilter("Migration bundle (*.zip);;All files (*)")

    def accept(self) -> None:
        selected = self.selectedFiles()
        if selected and Path(selected[0]).is_dir():
            self.done(QFileDialog.DialogCode.Accepted)
            return
        super().accept()


class RestorePage(BasePage):
    """Restore a bundle, verify it, and show the final report — all on one page."""

    _PHASES = ("restore", "verify", "report")

    def __init__(
        self,
        ui_state,
        run_restore_cb: Callable[[Path], dict],
        run_validation_cb: Callable[[], dict],
        generate_report_cb: Callable[[], dict],
        reset_restore_cb: Callable[[bool], dict],
    ) -> None:
        super().__init__(ui_state)
        self.run_restore_cb = run_restore_cb
        self.run_validation_cb = run_validation_cb
        self.generate_report_cb = generate_report_cb
        self.reset_restore_cb = reset_restore_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.bundle_path: Path | None = None
        self.report_paths: dict[str, str] = {}
        # When True, refresh() leaves self.status alone — set whenever a
        # phase result/error has set an explicit, meaningful message, so it
        # doesn't get silently overwritten by generic guidance text.
        self._sticky_status = False
        self._failed_phase: str | None = None
        self._build_ui()
        self._load_existing_report()
        self.refresh()

    def _load_existing_report(self) -> None:
        """Surface a report left over from a previous run of the app.

        report_paths/the report card are normally only populated right after
        a fresh restore→verify→report chain finishes in this session — so
        re-opening the app (or just navigating back to this page) after an
        earlier successful restore left no way to get back to that report.
        If final_report.json already exists on disk, load it so the report
        card and its Open Report buttons work immediately, no re-run needed.
        """
        if not FINAL_REPORT_JSON.exists():
            return
        try:
            report = json.loads(FINAL_REPORT_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        self._populate_report({
            "json_path": str(FINAL_REPORT_JSON),
            "markdown_path": str(FINAL_REPORT_MARKDOWN),
            "html_path": str(FINAL_REPORT_HTML),
            "report": report,
        })
        self._set_report_visible(True)
        self.ui_state.restore_completed = True
        self._sticky_status = True
        self.status.setText(
            "Showing the report from a previous restore on this computer. "
            "Click 'Reset Restored Files' first if you want to restore a different bundle."
        )

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🚀",
            "Welcome to Linux — restore your data",
            "Browse to your migration bundle and click Restore — nothing is "
            "overwritten without your confirmation.",
        ))

        bundle_card = QFrame()
        bundle_card.setProperty("card", "section")
        bundle_card_layout = QHBoxLayout(bundle_card)
        bundle_card_layout.setContentsMargins(14, 12, 14, 12)
        bundle_card_layout.setSpacing(8)

        self.bundle_edit = QLineEdit()
        self.bundle_edit.setReadOnly(True)
        self.bundle_edit.setPlaceholderText("No bundle selected")
        bundle_card_layout.addWidget(self.bundle_edit)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setProperty("role", "badge")
        self.browse_btn.clicked.connect(self._browse)
        bundle_card_layout.addWidget(self.browse_btn)

        root.addWidget(bundle_card)

        self.status = QLabel("")
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

        self.reset_btn = QPushButton("Reset Restored Files")
        self.reset_btn.setProperty("role", "badge")
        self.reset_btn.setToolTip("Delete the files copied during the last restore and start over")
        self.reset_btn.clicked.connect(self._reset)
        root.addWidget(self.reset_btn, alignment=Qt.AlignHCenter)

        # ── Recovery row — shown only when a phase fails ──────────────────────
        self.recovery_row = QHBoxLayout()
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setProperty("role", "badge")
        self.restart_btn.clicked.connect(self._restart)
        self.review_complete_btn = QPushButton("Review & Complete Anyway")
        self.review_complete_btn.setProperty("role", "cta")
        self.review_complete_btn.clicked.connect(self._review_and_complete)
        self.recovery_row.addStretch(1)
        self.recovery_row.addWidget(self.restart_btn)
        self.recovery_row.addWidget(self.review_complete_btn)
        self.recovery_row.addStretch(1)
        root.addLayout(self.recovery_row)
        self._set_recovery_visible(False)

        # ── Report card — shown only once the chain finishes ──────────────────
        self.report_card = QFrame()
        self.report_card.setProperty("card", "section")
        report_layout = self._make_report_card_layout(self.report_card)

        self.score_display = QLabel("Migration Score: —")
        self.score_display.setObjectName("HeroTitle")
        self.score_display.setAlignment(Qt.AlignCenter)
        report_layout.addWidget(self.score_display)

        self.summary_text = QTextEdit()
        self.summary_text.setObjectName("ReportView")
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(220)
        report_layout.addWidget(self.summary_text)

        btn_row = QHBoxLayout()
        self.open_markdown_btn = QPushButton("Open Report (Markdown)")
        self.open_markdown_btn.setProperty("role", "badge")
        self.open_markdown_btn.clicked.connect(self._open_markdown)
        self.open_html_btn = QPushButton("Open Report (Web page)")
        self.open_html_btn.setProperty("role", "badge")
        self.open_html_btn.clicked.connect(self._open_html)
        btn_row.addStretch(1)
        btn_row.addWidget(self.open_markdown_btn)
        btn_row.addWidget(self.open_html_btn)
        btn_row.addStretch(1)
        report_layout.addLayout(btn_row)

        self.finish_btn = QPushButton("🎉  Migration Complete — Finish")
        self.finish_btn.setProperty("role", "cta")
        self.finish_btn.setMinimumWidth(260)
        self.finish_btn.clicked.connect(self.request_finish.emit)
        report_layout.addWidget(self.finish_btn, alignment=Qt.AlignHCenter)

        root.addWidget(self.report_card)
        self.report_card.setVisible(False)

    @staticmethod
    def _make_report_card_layout(card: QFrame):
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        return layout

    def _set_recovery_visible(self, visible: bool) -> None:
        self.restart_btn.setVisible(visible)
        self.review_complete_btn.setVisible(visible)

    def _set_report_visible(self, visible: bool) -> None:
        self.report_card.setVisible(visible)

    # ── Bundle selection ─────────────────────────────────────────────────────

    def _browse(self) -> None:
        dialog = _BundlePickerDialog(self)
        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        selected_files = dialog.selectedFiles()
        if not selected_files:
            return
        selected_path = Path(selected_files[0])

        if selected_path.is_dir():
            # The unzipped bundle folder itself was selected directly.
            self.bundle_path = selected_path
            self.status.setText(f"Bundle folder selected: {self.bundle_path}")
        elif selected_path.suffix.lower() == ".zip":
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

    # ── Phase 1: restore ─────────────────────────────────────────────────────

    def _run_restore(self) -> None:
        if not self.bundle_path:
            self.status.setText("Please select a backup bundle archive or folder first.")
            self._sticky_status = True
            return
        if self.is_processing:
            return

        self._failed_phase = None
        self._set_recovery_visible(False)
        self._set_report_visible(False)
        self._sticky_status = True
        self.set_scanning(True)
        self.restore_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Restoring your files — this may take a few minutes depending on how much data you have...")

        worker = FunctionWorker(self.run_restore_cb, self.bundle_path)
        worker.signals.result.connect(self._on_restore_result)
        worker.signals.error.connect(lambda err: self._fail("restore", f"Restore failed.\n{user_facing_error(err)}", err))
        self.thread_pool.start(worker)

    def _on_restore_result(self, result: object) -> None:
        warnings: list[str] = []
        if isinstance(result, dict):
            self.ui_state.restore_completed = True
            warnings = result.get("warnings") or []
        else:
            self.ui_state.restore_completed = True
        self._restore_warnings = warnings
        self.status.setText("Files restored — verifying everything arrived safely...")
        self._run_verification()

    # ── Phase 2: verify ──────────────────────────────────────────────────────

    def _run_verification(self) -> None:
        worker = FunctionWorker(self.run_validation_cb)
        worker.signals.result.connect(self._on_verify_result)
        worker.signals.error.connect(lambda err: self._fail("verify", f"Verification failed.\n{user_facing_error(err)}", err))
        self.thread_pool.start(worker)

    def _on_verify_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.verification_completed = True
            self.ui_state.total_sovereignty_score = int(result.get("total_sovereignty_score", 0))
        self.status.setText("Verified — generating your migration report...")
        self._run_report()

    # ── Phase 3: report ──────────────────────────────────────────────────────

    def _run_report(self) -> None:
        worker = FunctionWorker(self.generate_report_cb)
        worker.signals.result.connect(self._on_report_result)
        worker.signals.error.connect(lambda err: self._fail("report", f"Report generation failed.\n{user_facing_error(err)}", err))
        self.thread_pool.start(worker)

    def _on_report_result(self, result: object) -> None:
        if isinstance(result, dict):
            self._populate_report(result)
        warnings = getattr(self, "_restore_warnings", [])
        if warnings:
            self._succeed(
                "✅  Your files have been restored, but a few optional steps couldn't complete:\n"
                + "\n".join(f"• {w}" for w in warnings)
            )
        else:
            self._succeed("🎉  Migration complete! Everything from your Windows machine is now on Linux.")

    def _populate_report(self, result: dict) -> None:
        self.report_paths = {
            "json": result.get("json_path", ""),
            "markdown": result.get("markdown_path", ""),
            "html": result.get("html_path", ""),
        }
        report = result.get("report", {})
        summary = report.get("summary", {})
        validation = report.get("validation", {})
        score = int(summary.get("score", 0))

        if score >= 90:
            score_label = f"🎉  Migration Score: {score}% — Outstanding!"
        elif score >= 70:
            score_label = f"✅  Migration Score: {score}% — Great result!"
        else:
            score_label = f"Migration Score: {score}% — See report for details"
        self.score_display.setText(score_label)

        rating = str(summary.get("rating", "Unknown"))
        restored = int(validation.get("restored_files", 0))
        total_files = int(validation.get("total_files", 0))
        coverage = f"{round(restored / total_files * 100)}%" if total_files else "—"
        score_color = "#1B5E20" if score >= 90 else ("#E65100" if score >= 70 else "#546E7A")
        score_bg = "#E8F5E9" if score >= 90 else ("#FFF3E0" if score >= 70 else "#ECEFF1")
        summary_rows = (
            self.html_row("Rating", self.html_pill(rating, score_color, score_bg))
            + self.html_row("Files restored", f"{restored} / {total_files} ({coverage})")
            + self.html_row("Hash verified", str(validation.get("hash_verified_files", 0)))
            + self.html_row("Hash failed", str(validation.get("hash_failed_files", 0)))
            + self.html_row("Apps mapped", str(validation.get("apps_mapped", 0)))
        )
        sections = [self.html_section("📊", "Migration Summary", f'<table style="width:100%;">{summary_rows}</table>')]

        def short(p: str) -> str:
            return ("…" + p[-52:]) if len(p) > 55 else p

        path_rows = (
            self.html_row("Markdown", f'<span style="color:#546E7A;font-size:14px;">{short(self.report_paths["markdown"])}</span>')
            + self.html_row("Web page", f'<span style="color:#546E7A;font-size:14px;">{short(self.report_paths["html"])}</span>')
            + self.html_row("JSON", f'<span style="color:#546E7A;font-size:14px;">{short(self.report_paths["json"])}</span>')
        )
        sections.append(self.html_section("📁", "Report Files", f'<table style="width:100%;">{path_rows}</table>'))

        self.summary_text.setHtml(self.html_wrap("".join(sections)))
        self.open_markdown_btn.setEnabled(bool(self.report_paths.get("markdown")))
        self.open_html_btn.setEnabled(bool(self.report_paths.get("html")))

    def _open_markdown(self) -> None:
        path = self.report_paths.get("markdown")
        if path:
            QDesktopServices.openUrl(Path(path).as_uri())

    def _open_html(self) -> None:
        path = self.report_paths.get("html")
        if path:
            QDesktopServices.openUrl(Path(path).as_uri())

    # ── Success / failure / recovery ─────────────────────────────────────────

    def _succeed(self, message: str) -> None:
        self.set_scanning(False)
        self.restore_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.loading.setVisible(False)
        self._sticky_status = True
        self._failed_phase = None
        self.status.setText(message)
        self._set_recovery_visible(False)
        self._set_report_visible(True)
        self.refresh()

    def _fail(self, phase: str, message: str, error: str) -> None:
        self.set_scanning(False)
        self.restore_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.ui_state.last_error = error
        self._sticky_status = True
        self._failed_phase = phase
        self.status.setText(message)
        self._set_recovery_visible(True)
        self.refresh()

    def _restart(self) -> None:
        self.bundle_path = None
        self.bundle_edit.clear()
        self.report_paths = {}
        self._restore_warnings = []
        self._failed_phase = None
        self.ui_state.restore_completed = False
        self.ui_state.verification_completed = False
        self.ui_state.total_sovereignty_score = 0
        self.ui_state.last_error = ""
        self._set_recovery_visible(False)
        self._set_report_visible(False)
        self._sticky_status = False
        self.status.setText("")
        self.refresh()

    def _review_and_complete(self) -> None:
        """Continue past whichever phase failed, using whatever succeeded so far."""
        phase = self._failed_phase
        self._set_recovery_visible(False)
        self.set_scanning(True)
        self.loading.setVisible(True)
        if phase == "restore":
            # Files may be partially restored — still worth verifying/reporting.
            self.status.setText("Continuing despite the earlier failure — verifying what arrived...")
            self.ui_state.restore_completed = True
            self._run_verification()
        elif phase == "verify":
            self.status.setText("Continuing despite the earlier failure — generating your report...")
            self._run_report()
        else:
            # Report generation itself failed — nothing more to chain into.
            self._succeed(
                "⚠️  Migration finished with errors. The full report couldn't be generated, "
                "but your files and verification results are still on this computer."
            )

    # ── Reset (undo everything the last restore did) ────────────────────────

    def _reset(self) -> None:
        if self.is_processing:
            return

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Reset this restore")
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setText("<b>Undo everything from the last restore?</b>")
        confirm.setInformativeText(
            "This removes the files that were copied, the desktop shortcuts/launchers "
            "that were created, and the wallpaper file that was copied in. The desktop "
            "look you had on Linux *before* the restore can't be brought back automatically "
            "(it was never recorded) — only what this tool itself added gets cleaned up.\n\n"
            "Your selected bundle stays untouched — you can restore again right after."
        )
        uninstall_checkbox = QCheckBox(
            "Also uninstall the apps that were installed during restore"
        )
        uninstall_checkbox.setChecked(False)
        uninstall_checkbox.setToolTip(
            "Off by default: if any of these packages are also relied on by other software "
            "already on this machine, removing them could affect that software too. Only "
            "check this if you're sure you want them gone."
        )
        confirm.setCheckBox(uninstall_checkbox)
        confirm.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes)
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        uninstall_apps = uninstall_checkbox.isChecked()
        self.set_scanning(True)
        self.loading.setVisible(True)
        self.status.setText(
            "Resetting — removing files, shortcuts, and settings"
            + (", and uninstalling apps" if uninstall_apps else "")
            + "..."
        )
        self._sticky_status = True

        worker = FunctionWorker(self.reset_restore_cb, uninstall_apps)
        worker.signals.result.connect(self._on_reset_result)
        worker.signals.error.connect(lambda err: self._on_reset_error(err))
        worker.signals.finished.connect(lambda: self.set_scanning(False))
        self.thread_pool.start(worker)

    def _on_reset_result(self, result: object) -> None:
        self.loading.setVisible(False)
        r = result if isinstance(result, dict) else {}

        self.ui_state.restore_completed = False
        self.ui_state.verification_completed = False
        self.ui_state.total_sovereignty_score = 0
        self.ui_state.last_error = ""
        self.report_paths = {}
        self._set_report_visible(False)

        parts = [f"{r.get('files_removed', 0)} file(s) removed"]
        if r.get("files_failed"):
            parts.append(f"{r['files_failed']} couldn't be deleted")
        parts.append(f"{r.get('shortcuts_removed', 0)} shortcut(s)/launcher(s) removed")
        if r.get("settings_files_removed"):
            parts.append(f"{r['settings_files_removed']} settings file(s) removed")
        apps_removed = r.get("apps_removed") or []
        apps_failed = r.get("apps_failed") or []
        if apps_removed:
            parts.append(f"{len(apps_removed)} app(s) uninstalled")
        if apps_failed:
            parts.append(f"{len(apps_failed)} app(s) could not be uninstalled: {', '.join(apps_failed)}")

        message = "Reset complete — " + ", ".join(parts) + ". Browse to a bundle to restore again."
        warnings = r.get("warnings") or []
        if warnings:
            message += "\n" + "\n".join(f"• {w}" for w in warnings)
        self.status.setText(message)
        self.refresh()

    def _on_reset_error(self, err: object) -> None:
        self.loading.setVisible(False)
        self.status.setText(f"Reset failed.\n{user_facing_error(err)}")
        self.refresh()

    # ── BasePage hooks ───────────────────────────────────────────────────────

    def can_proceed(self) -> bool:
        return True

    def refresh(self) -> None:
        self.restore_btn.setEnabled(self.bundle_path is not None)
        self.reset_btn.setEnabled(self.ui_state.restore_completed or RESTORE_REPORT.exists())
        if self._sticky_status:
            return
        if not self.ui_state.restore_completed and not self.is_processing and self.bundle_path is not None:
            self.status.setText("Bundle selected — click Restore to begin.")
