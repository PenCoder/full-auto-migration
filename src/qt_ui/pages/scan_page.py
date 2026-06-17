"""Scan page — inventory + compatibility analysis + app strategy, all in one step."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QRadioButton, QTextEdit

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker
from src.services.settings_service import SettingsMigrationService


class ScanPage(BasePage):
    """Inventory → compatibility analysis → app-strategy choice, all in one step."""

    def __init__(
        self,
        ui_state,
        run_inventory_cb: Callable[[bool], dict],
        run_analysis_cb: Callable[[], dict] | None = None,
        privacy_policy: dict[str, object] | None = None,
        current_step: int = 0,
        step_names: list[str] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.run_inventory_cb = run_inventory_cb
        self.run_analysis_cb = run_analysis_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Review", "Backup"]
        self.privacy_policy = privacy_policy or {}
        self.thread_pool = QThreadPool.globalInstance()
        self.last_scan_result: dict[str, object] = {}
        self.last_analysis_result: dict[str, object] = {}
        self._analysis_running = False
        self.settings_service = SettingsMigrationService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🔍",
            "Scan & Plan Your App Transition",
            "An inventory of your hardware and installed apps is collected, then each app is matched "
            "to a Linux alternative. Choose how much involvement you want in the process.",
        ))

        root.addWidget(
            self.create_trust_banner(
                "Your files are never read or sent anywhere — "
                "only app names and hardware details are used."
            )
        )

        report_title = QLabel("Scan results")
        report_title.setObjectName("SectionTitle")
        root.addWidget(report_title)

        self.scan_report_view = QTextEdit()
        self.scan_report_view.setObjectName("ReportView")
        self.scan_report_view.setReadOnly(True)
        self.scan_report_view.setMinimumHeight(200)
        self.scan_report_view.setMaximumHeight(280)
        self.scan_report_view.setPlaceholderText(
            "Scan results will appear here automatically when the page loads."
        )
        root.addWidget(self.scan_report_view)

        # App strategy question.
        self.migrate_all_radio = QRadioButton(
            "Switch all apps automatically — use the recommended alternatives"
        )
        self.migrate_all_hint = self.hint_label(
            "Best for most people. Every app is matched and all high-confidence alternatives are included."
        )
        self.choose_from_recommendations_radio = QRadioButton(
            "Show the recommendations and allow manual selection"
        )
        self.choose_from_recommendations_hint = self.hint_label(
            "Alternatives are suggested for each app and you decide which ones to include."
        )
        self.manual_mapping_radio = QRadioButton(
            "Manually specify which Linux app replaces each Windows app"
        )
        self.manual_mapping_hint = self.hint_label(
            "Full control — specify exactly which Linux app replaces each Windows app."
        )

        self.migrate_all_radio.toggled.connect(
            lambda checked: self._set_mapping_choice("migrate_all_supported", checked)
        )
        self.choose_from_recommendations_radio.toggled.connect(
            lambda checked: self._set_mapping_choice("choose_from_recommendations", checked)
        )
        self.manual_mapping_radio.toggled.connect(
            lambda checked: self._set_mapping_choice("manual_mapping", checked)
        )

        self.strategy_panel = self.create_guided_questionnaire(
            question="How would you like to handle your apps on Linux?",
            info=None,
            options=[
                self.migrate_all_radio,
                self.migrate_all_hint,
                self.choose_from_recommendations_radio,
                self.choose_from_recommendations_hint,
                self.manual_mapping_radio,
                self.manual_mapping_hint,
            ],
        )
        root.addWidget(self.strategy_panel)

        self.status = QLabel("Scanning your computer — just a moment…")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        _privacy_panel, self._privacy_label = self._make_info_panel("")
        root.addWidget(_privacy_panel)

        self._sync_radios_from_state()

    # ── Auto-trigger ─────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.ui_state.inventory_completed and not self.is_processing:
            QTimer.singleShot(300, lambda: self._run_scan())

    # ── Radio handlers ───────────────────────────────────────────────────────

    def _sync_radios_from_state(self) -> None:
        mode = self.ui_state.mapping_choice_mode
        if mode == "choose_from_recommendations":
            self.choose_from_recommendations_radio.setChecked(True)
        elif mode == "manual_mapping":
            self.manual_mapping_radio.setChecked(True)
        else:
            self.migrate_all_radio.setChecked(True)

    def _set_mapping_choice(self, mode: str, checked: bool) -> None:
        if not checked:
            return
        self.ui_state.mapping_choice_mode = mode
        self.refresh()

    # ── Scanning pipeline ────────────────────────────────────────────────────

    def _run_scan(self) -> None:
        if self.is_processing:
            return
        self.set_scanning(True)
        self.ui_state.is_scanning = True
        self.status.setText("Scanning your hardware and installed apps — this takes just a few seconds…")
        worker = FunctionWorker(lambda: self.run_inventory_cb(False))
        worker.signals.result.connect(self._on_scan_result)
        worker.signals.error.connect(self._on_scan_error)
        worker.signals.finished.connect(self._on_scan_finished)
        self.thread_pool.start(worker)

    def _on_scan_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.last_scan_result = result
            self.ui_state.inventory_completed = True
            settings = result.get("settings", {}) if isinstance(result.get("settings", {}), dict) else {}
            self.ui_state.settings_completed = bool(settings)
            self.ui_state.settings_inventory = settings
            shortcuts = result.get("shortcuts", {}) if isinstance(result.get("shortcuts", {}), dict) else {}
            self.ui_state.shortcuts_inventory = shortcuts
            self.ui_state.settings_migration_plan = (
                self.settings_service.build_plan(
                    settings,
                    self.ui_state.mode,
                    selections=self.ui_state.settings_selected_items,
                    migrate_enabled=self.ui_state.settings_migration_enabled,
                    shortcuts_inventory=shortcuts,
                )
                if settings
                else {}
            )
            hw = len(result.get("hardware", {}).keys())
            sw = len(result.get("software", {}).get("entries", []))
            self.status.setText(
                f"Scan complete — {hw} hardware categories, {sw} apps found. "
                "Matching Linux alternatives…"
            )
            # Chain: immediately run compatibility analysis.
            if self.run_analysis_cb:
                self._analysis_running = True
                self._run_analysis()
        else:
            self.status.setText("Scan finished but returned no results — you can still continue.")
        self._render_scan_report()

    def _run_analysis(self) -> None:
        worker = FunctionWorker(self.run_analysis_cb)
        worker.signals.result.connect(self._on_analysis_result)
        worker.signals.error.connect(self._on_analysis_error)
        worker.signals.finished.connect(self._on_analysis_finished)
        self.thread_pool.start(worker)

    def _on_analysis_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.last_analysis_result = result
            self.ui_state.analysis_completed = True
            matched = len(result.get("software", []))
            self.status.setText(
                f"✅  All done — Linux alternatives found for {matched} of your apps. "
                "Choose your preferred approach below, then click 'Next'."
            )
        self._render_scan_report()

    def _on_analysis_error(self, error: str) -> None:
        self.status.setText(
            "App matching ran into an issue — you can still continue to the next step."
        )
        self._render_scan_report()

    def _on_analysis_finished(self) -> None:
        self._analysis_running = False
        self.ui_state.is_scanning = False
        self.set_scanning(False)
        self.refresh()

    def _on_scan_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Scan ran into a problem.\n{user_facing_error(error)}")
        self._render_scan_report()

    def _on_scan_finished(self) -> None:
        # Hold the lock until analysis completes — they share the same processing state.
        if not self._analysis_running:
            self.ui_state.is_scanning = False
            self.set_scanning(False)
            self.refresh()

    # ── Report rendering ─────────────────────────────────────────────────────

    def _render_scan_report(self) -> None:
        mode = self.ui_state.mode.capitalize()
        inv_done = self.ui_state.inventory_completed
        analysis_done = bool(self.last_analysis_result)

        inv_pill = (
            self.html_pill("Done", "#1B5E20", "#E8F5E9") if inv_done else
            self.html_pill("Scanning…", "#E65100", "#FFF3E0")
        )
        match_pill = (
            self.html_pill("Done", "#1B5E20", "#E8F5E9") if analysis_done else (
                self.html_pill("Matching…", "#E65100", "#FFF3E0") if inv_done else
                self.html_pill("Pending", "#546E7A", "#ECEFF1")
            )
        )
        mode_pill = self.html_pill(mode, "#1565C0", "#E3F2FD")

        header = (
            f'<table style="width:100%;margin-bottom:14px;"><tr>'
            f'<td style="font-size:13px;color:#546E7A;">Mode&nbsp;{mode_pill}</td>'
            f'<td style="font-size:13px;color:#546E7A;text-align:center;">Scan&nbsp;{inv_pill}</td>'
            f'<td style="font-size:13px;color:#546E7A;text-align:right;">'
            f'App&nbsp;matching&nbsp;{match_pill}</td>'
            f'</tr></table>'
        )

        sections: list[str] = []

        if self.last_scan_result:
            hw = len(self.last_scan_result.get("hardware", {}).keys())
            sw = len(self.last_scan_result.get("software", {}).get("entries", []))
            depth = self.last_scan_result.get("software", {}).get("scan_depth", "quick")
            settings = (
                self.last_scan_result.get("settings", {})
                if isinstance(self.last_scan_result.get("settings", {}), dict)
                else {}
            )
            rows = (
                self.html_row("Scan depth", depth.capitalize())
                + self.html_row("Hardware categories", str(hw))
                + self.html_row("Software entries", str(sw))
            )
            if depth == "deep":
                deep = self.last_scan_result.get("software", {}).get("deep_scan_summary", {})
                rows += self.html_row("Via package manager", str(deep.get("package_manager_entries", 0)))
                rows += self.html_row("Via AppX / Store", str(deep.get("appx_entries", 0)))
            if settings:
                desktop = settings.get("desktop", {}) if isinstance(settings.get("desktop", {}), dict) else {}
                appearance = settings.get("appearance", {}) if isinstance(settings.get("appearance", {}), dict) else {}
                rows += self.html_row("Wallpaper captured", "Yes" if desktop.get("wallpaper_path") else "No")
                rows += self.html_row("Theme captured", "Yes" if appearance.get("current_theme") else "No")
            sections.append(self.html_section("🖥", "Scan Results", f'<table style="width:100%;">{rows}</table>'))
        else:
            sections.append(self.html_section("🖥", "Scan Results",
                self.html_empty("Scanning your computer — results will appear here shortly.")))

        if self.last_analysis_result:
            matched = len(self.last_analysis_result.get("software", []))
            hw_rows_count = len(self.last_analysis_result.get("hardware", []))
            rows = (
                self.html_row("Apps with Linux alternatives", str(matched))
                + self.html_row("Hardware advisories", str(hw_rows_count))
            )
            sections.append(self.html_section("📦", "App Matching", f'<table style="width:100%;">{rows}</table>'))
            recs = self.last_analysis_result.get("software", [])
            if recs:
                preview_rows = ""
                for rec in recs[:5]:
                    win = str(rec.get("windows_app", "") or rec.get("name", ""))
                    linux = str(rec.get("linux_package", "") or rec.get("linux_alternative", ""))
                    conf = str(rec.get("mapping_confidence", "") or rec.get("confidence", ""))
                    conf_color = {"high": "#1B5E20", "medium": "#E65100", "low": "#546E7A"}.get(conf, "#546E7A")
                    conf_bg = {"high": "#E8F5E9", "medium": "#FFF3E0", "low": "#ECEFF1"}.get(conf, "#ECEFF1")
                    preview_rows += (
                        f'<tr>'
                        f'<td style="padding:3px 10px 3px 0;font-size:13px;color:#0D1929;">{win}</td>'
                        f'<td style="padding:3px 10px 3px 0;font-size:13px;color:#1565C0;">{linux}</td>'
                        f'<td>{self.html_pill(conf, conf_color, conf_bg)}</td>'
                        f'</tr>'
                    )
                if len(recs) > 5:
                    preview_rows += (
                        f'<tr><td colspan="3" style="color:#90A4AE;font-size:12px;padding-top:4px;">'
                        f'+ {len(recs) - 5} more — full list on the Review page</td></tr>'
                    )
                sections.append(self.html_section("✅", "Top Matches",
                    f'<table style="width:100%;">{preview_rows}</table>'))
        elif self.ui_state.inventory_completed:
            sections.append(self.html_section("📦", "App Matching",
                self.html_empty("Matching your apps to Linux alternatives…")))

        if self.ui_state.last_error:
            err_body = (
                f'<div style="background:#FFF3E0;border-left:3px solid #E65100;'
                f'padding:8px 10px;border-radius:4px;font-size:13px;color:#BF360C;">'
                f'{self.ui_state.last_error}</div>'
            )
            sections.append(self.html_section("⚠", "Last Error", err_body))

        self.scan_report_view.setHtml(self.html_wrap(header + "".join(sections)))

    # ── Navigation guard ─────────────────────────────────────────────────────

    def can_proceed(self) -> bool:
        return self.ui_state.inventory_completed

    def blocked_reason(self) -> str:
        return "The scan needs to finish before you can continue — please wait a moment."

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        mode = self.ui_state.mode
        mapping_mode = self.ui_state.mapping_choice_mode

        software_online_enabled = bool(self.privacy_policy.get("software_online_lookup_enabled", True))
        self._privacy_label.setText(
            "Only software metadata is used for package matching — file content stays local."
            if software_online_enabled else
            "Online lookup is disabled — all processing is local."
        )

        # Mode-filtered strategy options — hide unavailable choices rather than disabling.
        if mode == "guided":
            self.choose_from_recommendations_radio.setVisible(False)
            self.choose_from_recommendations_hint.setVisible(False)
            self.manual_mapping_radio.setVisible(False)
            self.manual_mapping_hint.setVisible(False)
            if mapping_mode != "migrate_all_supported":
                self.ui_state.mapping_choice_mode = "migrate_all_supported"
                self.migrate_all_radio.setChecked(True)
        elif mode == "balanced":
            self.choose_from_recommendations_radio.setVisible(True)
            self.choose_from_recommendations_hint.setVisible(True)
            self.manual_mapping_radio.setVisible(False)
            self.manual_mapping_hint.setVisible(False)
            if mapping_mode == "manual_mapping":
                self.ui_state.mapping_choice_mode = "choose_from_recommendations"
                self.choose_from_recommendations_radio.setChecked(True)
        else:
            self.choose_from_recommendations_radio.setVisible(True)
            self.choose_from_recommendations_hint.setVisible(True)
            self.manual_mapping_radio.setVisible(True)
            self.manual_mapping_hint.setVisible(True)

        if self.ui_state.inventory_completed and not self.is_processing:
            if mode == "guided":
                self.status.setText("Scan complete — click 'Next' to continue.")
            else:
                self.status.setText("Scan complete — choose how to handle your apps below, then click 'Next'.")

        self._render_scan_report()
