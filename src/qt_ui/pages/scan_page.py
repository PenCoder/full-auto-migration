"""Scan page for inventory collection and recommendation generation."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QRadioButton, QTextEdit

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker
from src.services.settings_service import SettingsMigrationService


class ScanPage(BasePage):
    """Collect inventory and generate app-level recommendation previews."""

    def __init__(
        self,
        ui_state,
        run_inventory_cb: Callable[[bool], dict],
        run_recommendations_cb: Callable[[str, str], dict],
        privacy_policy: dict[str, object] | None = None,
        current_step: int = 0,
        step_names: list[str] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.run_inventory_cb = run_inventory_cb
        self.run_recommendations_cb = run_recommendations_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self.privacy_policy = privacy_policy or {}
        self.thread_pool = QThreadPool.globalInstance()
        self.is_running = False
        self.last_scan_result: dict[str, object] = {}
        self.last_recommendation_result: dict[str, object] = {}
        self._current_rec_strategy = "local"
        self.settings_service = SettingsMigrationService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🔍",
            "Let's see what's on your computer",
            "We'll take a quick look at your installed apps and hardware so nothing gets left behind. "
            "Your files are never read or sent anywhere — only app names and counts.",
        ))

        question = "Which apps should we find Linux replacements for?"
        info = (
            "• <b>Bring everything across</b> — we'll find a Linux alternative for every app we can.<br>"
            "• <b>Let me pick the important ones</b> — we'll focus on your highest-priority apps first."
        )

        self.migrate_all_radio = QRadioButton("Find replacements for all my apps")
        self.prioritize_radio = QRadioButton("Focus on my most important apps first")
        
        guided_panel = self.create_guided_questionnaire(
            question,
            info,
            options=[self.migrate_all_radio, self.prioritize_radio],
        )
        root.addWidget(guided_panel)

        if self.ui_state.recommendation_strategy == "prioritize":
            self.prioritize_radio.setChecked(True)
        else:
            self.migrate_all_radio.setChecked(True)

        self.recommendation_profile = QLabel("")
        self.recommendation_profile.setObjectName("BodyText")
        self.recommendation_profile.setWordWrap(True)
        self.recommendation_profile.setAlignment(Qt.AlignCenter)
        root.addWidget(self.recommendation_profile)

        self.mode_instruction = QLabel("")
        self.mode_instruction.setObjectName("BodyText")
        self.mode_instruction.setWordWrap(True)
        self.mode_instruction.setAlignment(Qt.AlignCenter)
        root.addWidget(self.mode_instruction)

        self.privacy_banner = QLabel("")
        self.privacy_banner.setObjectName("TrustBanner")
        self.privacy_banner.setWordWrap(True)
        self.privacy_banner.setAlignment(Qt.AlignCenter)
        root.addWidget(self.privacy_banner)

        self.status = QLabel("Ready to scan. Click the button below to discover your installed apps and hardware.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        scan_row = QHBoxLayout()
        scan_row.setSpacing(10)

        self.quick_scan_btn = QPushButton("Scan My Computer")
        self.quick_scan_btn.setProperty("role", "primary")
        self.quick_scan_btn.setFixedWidth(220)
        self.quick_scan_btn.clicked.connect(lambda: self._run_scan(deep_scan=False))
        scan_row.addWidget(self.quick_scan_btn)

        self.deep_scan_btn = QPushButton("Thorough Scan (finds more apps)")
        self.deep_scan_btn.setProperty("role", "primary")
        self.deep_scan_btn.setFixedWidth(260)
        self.deep_scan_btn.clicked.connect(lambda: self._run_scan(deep_scan=True))
        scan_row.addWidget(self.deep_scan_btn)

        root.addLayout(scan_row)

        rec_row = QHBoxLayout()
        rec_row.setSpacing(10)

        self.online_rec_btn = QPushButton("Check App Availability Online")
        self.online_rec_btn.setProperty("role", "badge")
        self.online_rec_btn.setMinimumHeight(42)
        self.online_rec_btn.setFixedWidth(240)
        self.online_rec_btn.clicked.connect(lambda: self._run_recommendations("online"))
        rec_row.addWidget(self.online_rec_btn)

        self.agent_rec_btn = QPushButton("Smart Recommendations (AI-powered)")
        self.agent_rec_btn.setProperty("role", "badge")
        self.agent_rec_btn.setMinimumHeight(42)
        self.agent_rec_btn.setFixedWidth(260)
        self.agent_rec_btn.clicked.connect(lambda: self._run_recommendations("agent"))
        rec_row.addWidget(self.agent_rec_btn)

        root.addLayout(rec_row)

        report_title = QLabel("What we found")
        report_title.setObjectName("StepTitle")
        report_title.setAlignment(Qt.AlignCenter)
        root.addWidget(report_title)

        self.scan_report_view = QTextEdit()
        self.scan_report_view.setReadOnly(True)
        self.scan_report_view.setMinimumHeight(170)
        self.scan_report_view.setMaximumHeight(250)
        self.scan_report_view.setPlaceholderText("Scan results and app matching summary will appear here after you run a scan.")
        self.scan_report_view.setStyleSheet(
            "QTextEdit {"
            " font-family: Consolas, 'Cascadia Mono', 'Courier New', monospace;"
            " font-size: 12px;"
            " border: 1px solid rgba(120,120,120,0.35);"
            " border-radius: 8px;"
            " padding: 10px;"
            " background: rgba(20, 24, 32, 0.05);"
            "}"
        )
        root.addWidget(self.scan_report_view)

        self.prioritize_radio.toggled.connect(self._on_priority_toggled)
        self.migrate_all_radio.toggled.connect(self._on_migrate_all_toggled)

    def _on_priority_toggled(self, checked: bool) -> None:
        if checked:
            self.ui_state.recommendation_strategy = "prioritize"
            self.refresh()

    def _on_migrate_all_toggled(self, checked: bool) -> None:
        if checked:
            self.ui_state.recommendation_strategy = "migrate_all"
        else:
            return
        self.refresh()

    def _set_running_state(self, running: bool) -> None:
        self.is_running = running
        self.quick_scan_btn.setEnabled(not running)
        self.deep_scan_btn.setEnabled(not running)
        self.online_rec_btn.setEnabled(not running)
        self.agent_rec_btn.setEnabled(not running)

    def _run_scan(self, deep_scan: bool) -> None:
        self._set_running_state(True)
        self.loading.setVisible(True)
        if deep_scan:
            self.status.setText("Running a thorough scan — this finds apps installed through all methods. Just a moment...")
            worker = FunctionWorker(lambda: self.run_inventory_cb(True))
        else:
            self.status.setText("Scanning your computer for installed apps and hardware. This only takes a few seconds...")
            worker = FunctionWorker(lambda: self.run_inventory_cb(False))
        worker.signals.result.connect(self._on_scan_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _run_recommendations(self, strategy: str) -> None:
        self._current_rec_strategy = strategy
        self._set_running_state(True)
        self.loading.setVisible(True)
        if strategy == "agent":
            self.status.setText("Using AI to find the best Linux alternatives for your apps. This may take a moment...")
        elif strategy == "local":
            self.status.setText("Matching your apps to their Linux equivalents...")
        else:
            self.status.setText("Checking online to confirm your apps are available for Linux...")
        preference = self.ui_state.recommendation_strategy
        worker = FunctionWorker(lambda: self.run_recommendations_cb(strategy, preference))
        worker.signals.result.connect(self._on_recommendation_result)
        worker.signals.error.connect(self._on_recommendation_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_scan_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.last_scan_result = result
            self.ui_state.inventory_completed = True
            self.ui_state.settings_completed = bool(result.get("settings"))
            self.ui_state.settings_inventory = result.get("settings", {}) if isinstance(result.get("settings", {}), dict) else {}
            self.ui_state.settings_migration_plan = (
                self.settings_service.build_plan(
                    self.ui_state.settings_inventory,
                    self.ui_state.mode,
                    selections=self.ui_state.settings_selected_items,
                    migrate_enabled=self.ui_state.settings_migration_enabled,
                )
                if self.ui_state.settings_inventory
                else {}
            )
            hw = len(result.get("hardware", {}).keys())
            sw = len(result.get("software", {}).get("entries", []))
            settings = result.get("settings", {}) if isinstance(result.get("settings", {}), dict) else {}
            scan_depth = result.get("software", {}).get("scan_depth", "quick")
            if scan_depth == "deep":
                deep = result.get("software", {}).get("deep_scan_summary", {})
                self.status.setText(
                    "Deep scan completed. "
                    f"Hardware categories: {hw}, registry apps: {sw}, "
                    f"package manager entries: {deep.get('package_manager_entries', 0)}, "
                    f"AppX entries: {deep.get('appx_entries', 0)}."
                )
            else:
                self.status.setText(
                    f"Quick scan completed. Captured {hw} hardware categories and {sw} software entries."
                )
            if settings:
                desktop = settings.get("desktop", {}) if isinstance(settings.get("desktop", {}), dict) else {}
                appearance = settings.get("appearance", {}) if isinstance(settings.get("appearance", {}), dict) else {}
                self.status.setText(
                    self.status.text()
                    + (
                        f" Settings captured: wallpaper={'yes' if desktop.get('wallpaper_path') else 'no'}, "
                        f"theme={'yes' if appearance.get('current_theme') else 'no'}."
                    )
                )

            if self.ui_state.mode == "guided":
                self.status.setText(
                    "Scan complete! Now finding the best Linux apps to replace your Windows ones..."
                )
                self._render_scan_report()
                self._run_recommendations("local")
                return
        else:
            self.status.setText("Scan finished but no results were returned.")
        if self.ui_state.settings_inventory:
            self.ui_state.settings_migration_plan = self.settings_service.build_plan(
                self.ui_state.settings_inventory,
                self.ui_state.mode,
                selections=self.ui_state.settings_selected_items,
                migrate_enabled=self.ui_state.settings_migration_enabled,
            )
        self._render_scan_report()
        self.refresh()

    def _on_recommendation_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.last_recommendation_result = result
            self.ui_state.analysis_completed = True
            count = int(result.get("recommended_count", 0))
            total = int(result.get("input_count", 0))
            strategy = str(result.get("strategy", "local"))
            if strategy == "agent":
                method = "AI-powered"
            elif strategy == "online":
                method = "Online-verified"
            else:
                method = "Local"
            self.status.setText(
                f"✅  {method} matching complete — we found Linux alternatives for {count} of your {total} apps. "
                "Click 'Continue' when ready."
            )
        else:
            self.status.setText("Matching finished. Click 'Continue' to review your app plan.")
        self._render_scan_report()
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Scan ran into a problem.\n{user_facing_error(error)}")
        self._render_scan_report()
        self.refresh()

    def _on_recommendation_error(self, error: str) -> None:
        if self._current_rec_strategy in ("agent", "online"):
            self.status.setText(
                f"The {'AI service' if self._current_rec_strategy == 'agent' else 'online lookup'} "
                "wasn't reachable — falling back to local matching now…"
            )
            self._run_recommendations("local")
        else:
            self.ui_state.last_error = error
            self.status.setText(f"Recommendation matching failed.\n{user_facing_error(error)}")
            self._render_scan_report()
            self.refresh()

    def _on_finished(self) -> None:
        self.is_running = False
        self.loading.setVisible(False)
        self.refresh()

    def _render_scan_report(self) -> None:
        mode = self.ui_state.mode.capitalize()
        lines: list[str] = []
        lines.append(f"Mode: {mode}")
        lines.append(f"Inventory completed: {'yes' if self.ui_state.inventory_completed else 'no'}")
        lines.append(f"Recommendations completed: {'yes' if self.ui_state.analysis_completed else 'no'}")
        lines.append("-" * 64)

        if self.last_scan_result:
            hw = len(self.last_scan_result.get("hardware", {}).keys())
            sw = len(self.last_scan_result.get("software", {}).get("entries", []))
            depth = self.last_scan_result.get("software", {}).get("scan_depth", "quick")
            settings = self.last_scan_result.get("settings", {}) if isinstance(self.last_scan_result.get("settings", {}), dict) else {}
            lines.append("Scan Snapshot")
            lines.append(f"  depth: {depth}")
            lines.append(f"  hardware categories: {hw}")
            lines.append(f"  software entries: {sw}")
            if depth == "deep":
                deep = self.last_scan_result.get("software", {}).get("deep_scan_summary", {})
                lines.append(f"  package manager entries: {deep.get('package_manager_entries', 0)}")
                lines.append(f"  appx entries: {deep.get('appx_entries', 0)}")
            if settings:
                desktop = settings.get("desktop", {}) if isinstance(settings.get("desktop", {}), dict) else {}
                appearance = settings.get("appearance", {}) if isinstance(settings.get("appearance", {}), dict) else {}
                exported = settings.get("exported_assets", {}) if isinstance(settings.get("exported_assets", {}), dict) else {}
                lines.append("  settings captured: yes")
                lines.append(f"  wallpaper: {desktop.get('wallpaper_path', 'n/a') or 'n/a'}")
                lines.append(f"  theme: {appearance.get('current_theme', 'n/a') or 'n/a'}")
                lines.append(f"  wallpaper export: {exported.get('wallpaper', '') or 'not exported'}")
                lines.append(f"  theme export: {exported.get('theme', '') or 'not exported'}")
            plan = self.ui_state.settings_migration_plan if isinstance(self.ui_state.settings_migration_plan, dict) else {}
            if plan:
                counts = plan.get("counts", {}) if isinstance(plan.get("counts", {}), dict) else {}
                lines.append("  settings migration plan")
                lines.append(f"    customization depth: {plan.get('customization_depth', 'n/a')}")
                lines.append(f"    auto migrate: {counts.get('auto_migrate', 0)}")
                lines.append(f"    suggest review: {counts.get('suggest_review', 0)}")
                lines.append(f"    manual review: {counts.get('manual_review', 0)}")
                lines.append(f"    excluded: {counts.get('excluded', 0)}")
        else:
            lines.append("Scan Snapshot")
            lines.append("  not available yet")

        lines.append("-" * 64)
        if self.last_recommendation_result:
            strategy = self.last_recommendation_result.get("strategy", "local")
            profile = self.last_recommendation_result.get("selection_profile", self.ui_state.recommendation_strategy)
            matched = self.last_recommendation_result.get("recommended_count", 0)
            total = self.last_recommendation_result.get("input_count", 0)
            report_path = self.last_recommendation_result.get("markdown_path", "")
            lines.append("Recommendation Snapshot")
            lines.append(f"  strategy: {strategy}")
            lines.append(f"  profile: {profile}")
            lines.append(f"  matched: {matched}/{total}")
            lines.append(f"  report: {report_path}")
        else:
            lines.append("Recommendation Snapshot")
            lines.append("  not available yet")

        if self.ui_state.last_error:
            lines.append("-" * 64)
            lines.append("Last Error")
            lines.append(f"  {self.ui_state.last_error}")

        plan = self.ui_state.settings_migration_plan if isinstance(self.ui_state.settings_migration_plan, dict) else {}
        if plan:
            lines.append("-" * 64)
            lines.append("Settings Migration Plan")
            lines.append(f"  depth: {plan.get('customization_depth', 'n/a')}")
            lines.append(f"  summary: {plan.get('summary', 'n/a')}")
            lines.append(f"  excluded: {plan.get('counts', {}).get('excluded', 0)}")
            for item in plan.get("items", [])[:8]:
                lines.append(
                    f"  - {item.get('name', '')}: {item.get('action', '')} ({item.get('confidence', '')})"
                )

        self.scan_report_view.setPlainText("\n".join(lines))

    def refresh(self) -> None:
        mode = self.ui_state.mode
        software_online_enabled = bool(self.privacy_policy.get("software_online_lookup_enabled", True))
        file_online_enabled = bool(self.privacy_policy.get("file_recommendation_online_enabled", False))
        if software_online_enabled:
            self.privacy_banner.setText(
                "Privacy: only software metadata is sent online for package lookup. File content and file usage signals stay local."
            )
        else:
            self.privacy_banner.setText(
                "Privacy: online software lookup is disabled. All recommendation processing is local."
            )
        if self.ui_state.recommendation_strategy == "prioritize":
            self.recommendation_profile.setText(
                "Recommendation profile: Prioritized shortlist. Focuses high-confidence and high-value applications first."
            )
        else:
            self.recommendation_profile.setText(
                "Recommendation profile: Migrate all. Keeps all supported applications in the recommendation set."
            )

        if mode == "guided":
            if self.ui_state.recommendation_strategy != "migrate_all":
                self.ui_state.recommendation_strategy = "migrate_all"
                self.migrate_all_radio.setChecked(True)
            self.mode_instruction.setText(
                "In Guided mode, one click does everything — we scan your computer and automatically find Linux equivalents for your apps."
            )
            self.quick_scan_btn.setText("Scan My Computer")
            self.deep_scan_btn.setVisible(False)
            self.online_rec_btn.setVisible(False)
            self.agent_rec_btn.setVisible(False)
            self.prioritize_radio.setEnabled(False)
            self.migrate_all_radio.setEnabled(False)
            if not self.is_running:
                self.quick_scan_btn.setEnabled(True)
            self.status.setText(
                "Guided mode uses quick inventory with auto-recommendation. Switch to Balanced or Expert for more controls."
                if not self.ui_state.inventory_completed
                else self.status.text()
            )
        elif mode == "balanced":
            self.mode_instruction.setText(
                "Choose a quick scan or a thorough one, then optionally verify app availability online."
            )
            self.quick_scan_btn.setText("Quick Scan")
            self.deep_scan_btn.setVisible(True)
            self.online_rec_btn.setVisible(software_online_enabled)
            self.agent_rec_btn.setVisible(False)
            self.prioritize_radio.setEnabled(True)
            self.migrate_all_radio.setEnabled(True)
            if not self.is_running:
                self.quick_scan_btn.setEnabled(True)
                self.deep_scan_btn.setEnabled(True)
                self.online_rec_btn.setEnabled(self.ui_state.inventory_completed and software_online_enabled)
            if not self.ui_state.inventory_completed:
                self.status.setText(
                    "Balanced mode unlocks deep scan and online recommendations while keeping agent automation disabled."
                )
        else:
            self.mode_instruction.setText(
                "Expert mode: choose scan depth, recommendation engine, and selection strategy — including AI-powered scoring."
            )
            self.quick_scan_btn.setText("Quick Scan")
            self.deep_scan_btn.setVisible(True)
            self.online_rec_btn.setVisible(software_online_enabled)
            self.agent_rec_btn.setVisible(software_online_enabled or file_online_enabled)
            self.prioritize_radio.setEnabled(True)
            self.migrate_all_radio.setEnabled(True)
            if not self.is_running:
                self.quick_scan_btn.setEnabled(True)
                self.deep_scan_btn.setEnabled(True)
                self.online_rec_btn.setEnabled(self.ui_state.inventory_completed and software_online_enabled)
                self.agent_rec_btn.setEnabled(self.ui_state.inventory_completed and (software_online_enabled or file_online_enabled))

            self._render_scan_report()

        # self.next_btn.setEnabled(self.ui_state.inventory_completed or self.ui_state.mode == "expert")
