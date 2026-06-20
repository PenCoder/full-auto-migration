"""Final report page for exporting migration evidence artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QTextEdit

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker
from src.services.report_service import ReportService
from src.services.settings_service import SettingsMigrationService


class ReportPage(BasePage):
    """Generate and open the final migration report outputs."""

    def __init__(self, ui_state, generate_report_cb: Callable[[], dict] | None = None) -> None:
        super().__init__(ui_state)
        self.generate_report_cb = generate_report_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.report_paths: dict[str, str] = {}
        self.settings_service = SettingsMigrationService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "📋",
            "Your Migration Report",
            "This is your official record of the migration — what was moved, what was verified, "
            "and your final Migration Score. You can save and share it.",
        ))

        root.addWidget(
            self.create_trust_banner(
                "This report is generated entirely on your computer. "
                "No data is uploaded or shared unless you choose to share the file."
            )
        )

        self.score_display = QLabel("Migration Score: —")
        self.score_display.setObjectName("HeroTitle")
        self.score_display.setAlignment(Qt.AlignCenter)
        root.addWidget(self.score_display)

        self.summary_text = QTextEdit()
        self.summary_text.setObjectName("ReportView")
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(220)
        root.addWidget(self.summary_text)

        self.report_status = QLabel("Click below to generate your full migration report in multiple formats you can save and share.")
        self.report_status.setObjectName("BodyText")
        self.report_status.setWordWrap(True)
        self.report_status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.report_status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.generate_btn = QPushButton("Re-generate Report")
        self.generate_btn.setProperty("role", "badge")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.setMinimumWidth(200)
        self.generate_btn.setVisible(False)
        self.generate_btn.clicked.connect(self._run_report_generation)
        root.addWidget(self.generate_btn, alignment=Qt.AlignHCenter)

        self.open_markdown_btn = QPushButton("Open Report (Markdown)")
        self.open_markdown_btn.setProperty("role", "cta")
        self.open_markdown_btn.setMinimumWidth(240)
        self.open_markdown_btn.clicked.connect(self._open_markdown)
        root.addWidget(self.open_markdown_btn, alignment=Qt.AlignHCenter)

        self.open_html_btn = QPushButton("Open Report (Web page)")
        self.open_html_btn.setProperty("role", "badge")
        self.open_html_btn.setMinimumWidth(240)
        self.open_html_btn.clicked.connect(self._open_html)
        root.addWidget(self.open_html_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("🎉  Migration Complete — Finish")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setMinimumWidth(260)
        self.next_btn.clicked.connect(self.request_finish.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.report_paths and not self.is_processing:
            QTimer.singleShot(300, self._run_report_generation)

    def _run_report_generation(self) -> None:
        if self.is_processing:
            return
        self.generate_btn.setEnabled(False)
        self.open_markdown_btn.setEnabled(False)
        self.open_html_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.set_scanning(True)
        self.report_status.setText("Generating report artifacts and visual summary...")

        if self.generate_report_cb is not None:
            worker = FunctionWorker(self.generate_report_cb)
        else:
            worker = FunctionWorker(self._default_generate_report)

        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _default_generate_report(self) -> dict:
        service = ReportService()
        return service.generate_report()

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.report_paths = {
                "json": result.get("json_path", ""),
                "markdown": result.get("markdown_path", ""),
                "html": result.get("html_path", ""),
            }
            report = result.get("report", {})
            summary = report.get("summary", {})
            validation = report.get("validation", {})
            score = int(summary.get("score", 0))
            self.ui_state.total_sovereignty_score = score

            if score >= 90:
                score_label = f"🎉  Migration Score: {score}% — Outstanding!"
            elif score >= 70:
                score_label = f"✅  Migration Score: {score}% — Great result!"
            else:
                score_label = f"Migration Score: {score}% — See report for details"
            self.score_display.setText(score_label)

            # ── Score + files section ──────────────────────────────────────
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
            sections = [self.html_section("📊", "Migration Summary",
                f'<table style="width:100%;">{summary_rows}</table>')]

            # ── Report file paths ──────────────────────────────────────────
            def short(p: str) -> str:
                return ("…" + p[-52:]) if len(p) > 55 else p

            path_rows = (
                self.html_row("Markdown", f'<span style="color:#546E7A;font-size: 14px;">{short(self.report_paths["markdown"])}</span>')
                + self.html_row("Web page", f'<span style="color:#546E7A;font-size: 14px;">{short(self.report_paths["html"])}</span>')
                + self.html_row("JSON", f'<span style="color:#546E7A;font-size: 14px;">{short(self.report_paths["json"])}</span>')
            )
            sections.append(self.html_section("📁", "Report Files",
                f'<table style="width:100%;">{path_rows}</table>'))

            # ── Settings snapshot (optional) ──────────────────────────────
            settings = self.ui_state.settings_inventory if isinstance(self.ui_state.settings_inventory, dict) else {}
            if settings:
                desktop = settings.get("desktop", {}) if isinstance(settings.get("desktop", {}), dict) else {}
                appearance = settings.get("appearance", {}) if isinstance(settings.get("appearance", {}), dict) else {}
                exported = settings.get("exported_assets", {}) if isinstance(settings.get("exported_assets", {}), dict) else {}
                shortcuts = self.ui_state.shortcuts_inventory if isinstance(self.ui_state.shortcuts_inventory, dict) else {}
                sc_counts = shortcuts.get("counts", {}) if isinstance(shortcuts.get("counts", {}), dict) else {}
                snap_rows = (
                    self.html_row("Wallpaper", desktop.get("wallpaper_path", "n/a") or "n/a")
                    + self.html_row("Theme", appearance.get("current_theme", "n/a") or "n/a")
                    + self.html_row("Wallpaper export", exported.get("wallpaper", "") or "not exported")
                    + self.html_row("Theme export", exported.get("theme", "") or "not exported")
                    + self.html_row(
                        "App shortcuts",
                        f"{sc_counts.get('matched', 0)} matched "
                        f"(Desktop {sc_counts.get('desktop', 0)}, "
                        f"Start Menu {sc_counts.get('start_menu', 0)}, "
                        f"Taskbar {sc_counts.get('taskbar', 0)})"
                        if sc_counts else "n/a",
                    )
                )
                sections.append(self.html_section("🖥️", "Settings Snapshot",
                    f'<table style="width:100%;">{snap_rows}</table>'))

            # ── Settings plan (optional) ───────────────────────────────────
            plan = self.ui_state.settings_migration_plan if isinstance(self.ui_state.settings_migration_plan, dict) else {}
            if plan:
                plan_paths = self.settings_service.write_plan(plan)
                counts = plan.get("counts", {}) if isinstance(plan.get("counts", {}), dict) else {}
                plan_rows = (
                    self.html_row("Depth", str(plan.get("customization_depth", "n/a")).capitalize())
                    + self.html_row("Auto-migrate", str(counts.get("auto_migrate", 0)))
                    + self.html_row("Suggest review", str(counts.get("suggest_review", 0)))
                    + self.html_row("Manual review", str(counts.get("manual_review", 0)))
                    + self.html_row("Excluded", str(counts.get("excluded", 0)))
                    + self.html_row("Plan Markdown", f'<span style="color:#546E7A;font-size: 14px;">{short(plan_paths.get("markdown_path", ""))}</span>')
                )
                sections.append(self.html_section("📋", "Settings Migration Plan",
                    f'<table style="width:100%;">{plan_rows}</table>'))

            self.summary_text.setHtml(self.html_wrap("".join(sections)))
            self.report_status.setText("Your report is ready! Use the buttons below to open it — you can save or print it from there.")
            self.ui_state.verification_completed = True
        else:
            self.report_status.setText("Report generation finished without structured output.")

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.report_status.setText(f"Report generation failed.\n{user_facing_error(error)}")

    def _on_finished(self) -> None:
        self.generate_btn.setVisible(True)
        self.generate_btn.setEnabled(True)
        self.open_markdown_btn.setEnabled(bool(self.report_paths.get("markdown")))
        self.open_html_btn.setEnabled(bool(self.report_paths.get("html")))
        self.next_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.set_scanning(False)
        self.refresh()

    def _open_markdown(self) -> None:
        path = self.report_paths.get("markdown")
        if path:
            QDesktopServices.openUrl(Path(path).as_uri())

    def _open_html(self) -> None:
        path = self.report_paths.get("html")
        if path:
            QDesktopServices.openUrl(Path(path).as_uri())

    def can_proceed(self) -> bool:
        return bool(self.report_paths)

    def refresh(self) -> None:
        self.next_btn.setEnabled(bool(self.report_paths))
