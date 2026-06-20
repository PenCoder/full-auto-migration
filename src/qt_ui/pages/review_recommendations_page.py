"""Review page for app and file migration recommendations."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTextEdit,
)

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ReviewRecommendationsPage(BasePage):
    """Present a full summary of all migration choices before backup."""

    def __init__(
        self,
        ui_state,
        run_app_recommendations_cb: Callable[[], dict],
        run_file_recommendations_cb: Callable[[], dict],
        on_selection_changed: Callable[[dict], None] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.run_app_recommendations_cb = run_app_recommendations_cb
        self.run_file_recommendations_cb = run_file_recommendations_cb
        self.on_selection_changed = on_selection_changed
        self.thread_pool = QThreadPool.globalInstance()
        self.app_recommendations: dict[str, Any] = {}
        self.file_recommendations: dict[str, Any] = {}
        self._all_recs: list = []
        self._item_checked: dict[str, bool] = {}
        self.is_running = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🔍",
            "Review & Confirm Your Migration Plan",
            "A summary of all choices made so far. "
            "Look through the details and click 'Continue' when ready.",
        ))

        root.addWidget(
            self.create_trust_banner(
                "Nothing is moved yet. This is a preview only. "
                "All files stay on your Windows machine until the backup step."
            )
        )

        # ── Configuration summary ────────────────────────────────────────────
        config_title = QLabel("Your configuration")
        config_title.setObjectName("SectionTitle")
        root.addWidget(config_title)

        self.config_summary = QTextEdit()
        self.config_summary.setObjectName("ReportView")
        self.config_summary.setReadOnly(True)
        self.config_summary.setMinimumHeight(110)
        self.config_summary.setMaximumHeight(160)
        root.addWidget(self.config_summary)

        # ── App recommendations ──────────────────────────────────────────────
        app_title = QLabel("Apps — Linux alternatives")
        app_title.setObjectName("SectionTitle")
        root.addWidget(app_title)

        self.app_summary = QLabel(
            "Loading app recommendations — Linux alternatives for your Windows apps will appear here."
        )
        self.app_summary.setObjectName("BodyText")
        self.app_summary.setWordWrap(True)
        root.addWidget(self.app_summary)

        self.app_details = QTextEdit()
        self.app_details.setObjectName("ReportView")
        self.app_details.setReadOnly(True)
        self.app_details.setMinimumHeight(120)
        self.app_details.setMaximumHeight(180)
        root.addWidget(self.app_details)

        self.app_checklist = QListWidget()
        self.app_checklist.setObjectName("ReportView")
        self.app_checklist.setMinimumHeight(120)
        self.app_checklist.setMaximumHeight(180)
        self.app_checklist.setVisible(False)
        self.app_checklist.itemChanged.connect(self._on_app_item_changed)
        root.addWidget(self.app_checklist)

        # ── File recommendations ─────────────────────────────────────────────
        file_title = QLabel("Files — what's included")
        file_title.setObjectName("SectionTitle")
        root.addWidget(file_title)

        self.file_summary = QLabel(
            "Loading file recommendations — selected files for migration will appear here."
        )
        self.file_summary.setObjectName("BodyText")
        self.file_summary.setWordWrap(True)
        root.addWidget(self.file_summary)

        self.file_details = QTextEdit()
        self.file_details.setObjectName("ReportView")
        self.file_details.setReadOnly(True)
        self.file_details.setMinimumHeight(120)
        self.file_details.setMaximumHeight(180)
        root.addWidget(self.file_details)

        # ── Status / progress ────────────────────────────────────────────────
        self.status = QLabel("Ready.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.next_btn = QPushButton("Looks good — Continue to Backup")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setMinimumWidth(280)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    # ── Configuration summary renderer ──────────────────────────────────────

    def _render_config_summary(self) -> None:
        mode = self.ui_state.mode

        mode_row = self.html_row("Migration mode", mode.capitalize())

        # Settings / appearance
        if not self.ui_state.settings_migration_enabled:
            appearance_val = "Disabled"
        else:
            label_map = {
                "wallpaper": "Wallpaper",
                "theme": "Theme",
                "light_dark": "Light/Dark",
                "accent_color": "Accent color",
                "taskbar_layout": "App shortcuts",
                "keyboard_shortcuts": "Keyboard shortcuts",
                "file_associations": "File associations",
            }
            selected = []
            for k, v in self.ui_state.settings_selected_items.items():
                if not v or k not in label_map:
                    continue
                label = label_map[k]
                if k == "taskbar_layout":
                    counts = self.ui_state.shortcuts_inventory.get("counts", {}) \
                        if isinstance(self.ui_state.shortcuts_inventory, dict) else {}
                    matched = int(counts.get("matched", 0)) if isinstance(counts, dict) else 0
                    if matched:
                        label = f"{label} ({matched} matched)"
                selected.append(label)
            appearance_val = ", ".join(selected) if selected else "None selected"
        appearance_row = self.html_row("Appearance", appearance_val)

        # Data strategy
        choice_labels = {
            "all_files": "All files",
            "selected_types": "Selected file types",
            "ai_recommended": "Usage-based recommendation",
            "manual": "Manual (skipped)",
        }
        data_row = self.html_row(
            "File strategy",
            choice_labels.get(self.ui_state.data_choice_mode, "All files"),
        )

        # Folder scope
        folders = [k for k, v in self.ui_state.selected_folders.items() if v]
        custom = [p for p in (self.ui_state.custom_paths or []) if p]
        folder_display = ", ".join(folders) if folders else "None"
        if custom:
            folder_display += f" + {len(custom)} custom path(s)"
        folders_row = self.html_row("Folders", folder_display)

        # Target distro
        distro_row = self.html_row("Target distro", self.ui_state.target_distro)

        body = f'<table style="width:100%;">{mode_row}{appearance_row}{data_row}{folders_row}{distro_row}</table>'
        self.config_summary.setHtml(self.html_wrap(self.html_section("⚙️", "Configuration", body)))

    # ── Recommendation generation ────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.is_processing and not self.app_recommendations and not self.file_recommendations:
            QTimer.singleShot(300, self._run_recommendations)

    def _run_recommendations(self) -> None:
        if self.is_processing:
            return
        self._set_running_state(True)
        self.loading.setVisible(True)
        self.status.setText("Building migration plan…")

        def _generate_both() -> tuple[dict, dict]:
            try:
                apps = self.run_app_recommendations_cb()
            except Exception as e:
                apps = {"error": str(e)}
            try:
                files = self.run_file_recommendations_cb()
            except Exception as e:
                files = {"error": str(e)}
            return apps, files

        worker = FunctionWorker(_generate_both)
        worker.signals.result.connect(self._on_recommendations_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_recommendations_result(self, result: object) -> None:
        if isinstance(result, tuple) and len(result) == 2:
            app_recs, file_recs = result

            if isinstance(app_recs, dict) and "error" not in app_recs:
                self.app_recommendations = app_recs
                app_count = int(app_recs.get("recommended_count", 0))
                app_total = int(app_recs.get("input_count", 0))
                self.app_summary.setText(
                    f"Linux alternatives found for {app_count} of {app_total} Windows apps."
                )
                recs = app_recs.get("recommendations", [])
                if recs:
                    conf_color = {"high": "#1B5E20", "medium": "#E65100", "low": "#546E7A"}
                    conf_bg = {"high": "#E8F5E9", "medium": "#FFF3E0", "low": "#ECEFF1"}
                    rows = ""
                    for rec in recs:
                        win = str(rec.get("windows_app", ""))
                        linux = str(rec.get("linux_package", ""))
                        conf = str(rec.get("mapping_confidence", ""))
                        badge = self.html_pill(
                            conf, conf_color.get(conf, "#546E7A"), conf_bg.get(conf, "#ECEFF1")
                        )
                        rows += (
                            f'<tr>'
                            f'<td style="padding:3px 10px 3px 0;font-size: 15px;color:#1B1E28;">✓ {win}</td>'
                            f'<td style="padding:3px 10px 3px 0;font-size: 15px;color:#3F6FE0;">{linux}</td>'
                            f'<td style="padding:3px 0;">{badge}</td>'
                            f'</tr>'
                        )
                    body = (
                        f'<table style="width:100%;">'
                        f'<tr>'
                        f'<th style="text-align:left;color:#90A4AE;font-size: 13px;font-weight:600;padding-bottom:4px;">Windows App</th>'
                        f'<th style="text-align:left;color:#90A4AE;font-size: 13px;font-weight:600;padding-bottom:4px;">Linux Package</th>'
                        f'<th style="text-align:left;color:#90A4AE;font-size: 13px;font-weight:600;padding-bottom:4px;">Match</th>'
                        f'</tr>{rows}</table>'
                    )
                else:
                    body = self.html_empty("No app recommendations available.")
                self.app_details.setHtml(self.html_wrap(body))

                # Populate interactive checklist for choose_from_recommendations mode.
                self._all_recs = recs
                self._item_checked = {}
                self.app_checklist.blockSignals(True)
                self.app_checklist.clear()
                for rec in recs:
                    win = str(rec.get("windows_app", ""))
                    linux = str(rec.get("linux_package", ""))
                    conf = str(rec.get("mapping_confidence", ""))
                    item = QListWidgetItem(f"{win}  →  {linux}  ({conf})")
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked)
                    item.setData(Qt.UserRole, win)
                    self._item_checked[win] = True
                    self.app_checklist.addItem(item)
                self.app_checklist.blockSignals(False)
            else:
                self.app_summary.setText(
                    "App recommendations could not be generated — you can continue anyway."
                )
                self.app_details.setHtml(self.html_wrap(self.html_empty("No app recommendations available.")))

            if isinstance(file_recs, dict) and "error" not in file_recs:
                self.file_recommendations = file_recs
                file_count = int(file_recs.get("recommended_count", 0))
                file_total = int(file_recs.get("input_count", 0))
                self.file_summary.setText(
                    f"{file_count} of {file_total} selected files will be included in the migration bundle."
                )
                recs = file_recs.get("recommendations", [])
                if recs:
                    imp_color = {"critical": "#B71C1C", "important": "#1B3A86", "useful": "#1B5E20", "low": "#6B7390"}
                    imp_bg = {"critical": "#FFEBEE", "important": "#DCE6FF", "useful": "#E8F5E9", "low": "#ECEFF1"}
                    rows = ""
                    for rec in recs:
                        path = str(rec.get("file_path", ""))
                        short_path = ("…" + path[-45:]) if len(path) > 48 else path
                        imp = str(rec.get("importance", "low"))
                        badge = self.html_pill(imp, imp_color.get(imp, "#546E7A"), imp_bg.get(imp, "#ECEFF1"))
                        rows += (
                            f'<tr>'
                            f'<td style="padding:3px 10px 3px 0;font-size: 14px;color:#1B1E28;'
                            f'font-family:\'Cascadia Mono\',monospace;">✓ {short_path}</td>'
                            f'<td style="padding:3px 0;">{badge}</td>'
                            f'</tr>'
                        )
                    body = f'<table style="width:100%;">{rows}</table>'
                else:
                    body = self.html_empty("No file recommendations available.")
                self.file_details.setHtml(self.html_wrap(body))
            else:
                self.file_summary.setText(
                    "File recommendations could not be generated — you can continue anyway."
                )
                self.file_details.setHtml(self.html_wrap(self.html_empty("No file recommendations available.")))

            self.ui_state.analysis_completed = True
            self.status.setText("Migration plan ready. Review the details above, then click 'Continue to Backup'.")
        else:
            self.status.setText("Something unexpected happened — try refreshing the plan again.")

        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Could not generate recommendations.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self._set_running_state(False)
        self.loading.setVisible(False)
        self.refresh()

    def _set_running_state(self, running: bool) -> None:
        self.is_running = running
        self.set_scanning(running)
        self.next_btn.setEnabled(not running)

    def _on_app_item_changed(self, item: QListWidgetItem) -> None:
        key = str(item.data(Qt.UserRole))
        self._item_checked[key] = item.checkState() == Qt.Checked
        self._write_back_selection()

    def _write_back_selection(self) -> None:
        if not self.on_selection_changed or not self.app_recommendations:
            return
        filtered = [
            r for r in self._all_recs
            if self._item_checked.get(str(r.get("windows_app", "")), True)
        ]
        result = {**self.app_recommendations, "recommendations": filtered, "recommended_count": len(filtered)}
        self.on_selection_changed(result)

    def refresh(self) -> None:
        self._render_config_summary()

        is_interactive = self.ui_state.mapping_choice_mode == "choose_from_recommendations"
        self.app_details.setVisible(not is_interactive)
        self.app_checklist.setVisible(is_interactive and bool(self.app_recommendations))

        if not self.is_running:
            if not self.app_recommendations:
                self.status.setText("Loading the migration plan — just a moment…")
            elif is_interactive:
                self.status.setText(
                    "Check or uncheck apps to include in the bundle, then click 'Continue to Backup'."
                )
            else:
                self.status.setText("Migration plan ready. Review the details above, then click 'Continue to Backup'.")

        self.next_btn.setEnabled(not self.is_running)
