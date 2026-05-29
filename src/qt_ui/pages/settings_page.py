"""Settings migration page for choosing desktop preferences to carry over."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QTextEdit

from src.qt_ui.pages.base_page import BasePage
from src.services.settings_service import SettingsMigrationService


class SettingsPage(BasePage):
    """Let the user choose which Windows settings should be migrated."""

    def __init__(self, ui_state, current_step: int = 3, step_names: list[str] | None = None) -> None:
        super().__init__(ui_state)
        self.current_step = current_step
        self.step_names = step_names or ["Mode", "Scan", "Settings", "Data", "Apps", "Review", "Backup"]
        self.settings_service = SettingsMigrationService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout(max_width=980)

        root.addWidget(self.create_page_header(
            "🖥️",
            "Bring your desktop look with you",
            "Your wallpaper, colors, and theme can follow you to Linux so it feels familiar from day one.",
        ))

        self.status = QLabel("Choose which parts of your Windows appearance you'd like to carry across.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.migrate_toggle = QCheckBox("Yes — carry over my Windows look and feel")
        self.migrate_toggle.setChecked(True)
        self.migrate_toggle.toggled.connect(lambda _: self._on_toggle_changed())
        root.addWidget(self.migrate_toggle, alignment=Qt.AlignHCenter)

        self.guided_panel = self._build_guided_panel()
        self.balanced_panel = self._build_balanced_panel()
        self.expert_panel = self._build_expert_panel()
        root.addWidget(self.guided_panel)
        root.addWidget(self.balanced_panel)
        root.addWidget(self.expert_panel)

        self.preview = QTextEdit()
        self.preview.setObjectName("ReportView")
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(190)
        root.addWidget(self.preview)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _build_guided_panel(self):
        panel = self.create_guided_questionnaire(
            "Your desktop appearance — quick and simple",
            "We'll copy over your wallpaper and color theme automatically. No decisions needed.",
            options=[],
        )
        self.guided_wallpaper = QCheckBox("Copy my wallpaper / background image")
        self.guided_wallpaper.setChecked(True)
        self.guided_theme = QCheckBox("Copy my color theme")
        self.guided_theme.setChecked(True)
        self.guided_theme.setEnabled(False)
        self.guided_wallpaper.toggled.connect(self._sync_selections)
        panel.layout().addWidget(self.guided_wallpaper)
        panel.layout().addWidget(self.guided_theme)
        return panel

    def _build_balanced_panel(self):
        panel = self.create_guided_questionnaire(
            "Choose what to bring across",
            "Tick the appearance items you'd like to keep. Untick anything you'd rather set up fresh on Linux.",
            options=[],
        )
        self.balanced_wallpaper = QCheckBox("Wallpaper")
        self.balanced_wallpaper.setChecked(True)
        self.balanced_theme = QCheckBox("Theme file")
        self.balanced_theme.setChecked(True)
        self.balanced_light_dark = QCheckBox("Light/Dark preference")
        self.balanced_light_dark.setChecked(True)
        self.balanced_accent = QCheckBox("Accent color")
        self.balanced_accent.setChecked(True)
        for checkbox in [self.balanced_wallpaper, self.balanced_theme, self.balanced_light_dark, self.balanced_accent]:
            checkbox.toggled.connect(self._sync_selections)
            panel.layout().addWidget(checkbox)
        return panel

    def _build_expert_panel(self):
        panel = self.create_guided_questionnaire(
            "Full control over your desktop appearance",
            "All appearance items are shown, including advanced settings that may need a manual tweak on Linux.",
            options=[],
        )
        self.expert_wallpaper = QCheckBox("Wallpaper")
        self.expert_wallpaper.setChecked(True)
        self.expert_theme = QCheckBox("Theme file")
        self.expert_theme.setChecked(True)
        self.expert_light_dark = QCheckBox("Light/Dark preference")
        self.expert_light_dark.setChecked(True)
        self.expert_accent = QCheckBox("Accent color")
        self.expert_accent.setChecked(True)
        self.expert_taskbar = QCheckBox("Taskbar / panel layout")
        self.expert_shortcuts = QCheckBox("Keyboard shortcuts")
        self.expert_associations = QCheckBox("File associations")
        for checkbox in [
            self.expert_wallpaper,
            self.expert_theme,
            self.expert_light_dark,
            self.expert_accent,
            self.expert_taskbar,
            self.expert_shortcuts,
            self.expert_associations,
        ]:
            checkbox.toggled.connect(self._sync_selections)
            panel.layout().addWidget(checkbox)
        return panel

    def _on_toggle_changed(self) -> None:
        self._sync_selections()

    def _sync_selections(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided":
            selections = {
                "wallpaper": self.guided_wallpaper.isChecked(),
                "theme": self.guided_theme.isChecked(),
                "light_dark": False,
                "accent_color": False,
                "taskbar_layout": False,
                "keyboard_shortcuts": False,
                "file_associations": False,
            }
        elif mode == "balanced":
            selections = {
                "wallpaper": self.balanced_wallpaper.isChecked(),
                "theme": self.balanced_theme.isChecked(),
                "light_dark": self.balanced_light_dark.isChecked(),
                "accent_color": self.balanced_accent.isChecked(),
                "taskbar_layout": False,
                "keyboard_shortcuts": False,
                "file_associations": False,
            }
        else:
            selections = {
                "wallpaper": self.expert_wallpaper.isChecked(),
                "theme": self.expert_theme.isChecked(),
                "light_dark": self.expert_light_dark.isChecked(),
                "accent_color": self.expert_accent.isChecked(),
                "taskbar_layout": self.expert_taskbar.isChecked(),
                "keyboard_shortcuts": self.expert_shortcuts.isChecked(),
                "file_associations": self.expert_associations.isChecked(),
            }

        self.ui_state.settings_migration_enabled = self.migrate_toggle.isChecked()
        self.ui_state.settings_selected_items = selections
        self._rebuild_plan()
        self._update_preview()

    def _rebuild_plan(self) -> None:
        inventory = self.ui_state.settings_inventory if isinstance(self.ui_state.settings_inventory, dict) else {}
        if inventory:
            self.ui_state.settings_migration_plan = self.settings_service.build_plan(
                inventory,
                self.ui_state.mode,
                selections=self.ui_state.settings_selected_items,
                migrate_enabled=self.ui_state.settings_migration_enabled,
            )
        else:
            self.ui_state.settings_migration_plan = {}

    def refresh(self) -> None:
        mode = self.ui_state.mode
        self.migrate_toggle.setChecked(self.ui_state.settings_migration_enabled)

        self.guided_panel.setVisible(mode == "guided")
        self.balanced_panel.setVisible(mode == "balanced")
        self.expert_panel.setVisible(mode == "expert")

        if not self.ui_state.settings_inventory:
            self.status.setText("Complete the scan step first — we need to read your current Windows appearance before we can copy it.")
        elif mode == "guided":
            self.status.setText("We've detected your wallpaper and theme. We'll carry them across automatically — no action needed.")
        elif mode == "balanced":
            self.status.setText("Tick the items below that you'd like to keep on Linux. Untick anything you'd prefer to set up fresh.")
        else:
            self.status.setText("All appearance options are shown. Items marked for manual review may need a small tweak after migration.")

        self._sync_selections()
        self._update_preview()

    def _update_preview(self) -> None:
        plan = self.ui_state.settings_migration_plan if isinstance(self.ui_state.settings_migration_plan, dict) else {}
        if not plan:
            self.preview.setHtml(self.html_wrap(
                self.html_section("🖥️", "Settings Migration Plan",
                    self.html_empty("Complete the scan step first — your settings plan will appear here."))
            ))
            return

        counts = plan.get("counts", {}) if isinstance(plan.get("counts", {}), dict) else {}
        depth = str(plan.get("customization_depth", "n/a")).capitalize()
        summary = str(plan.get("summary", ""))

        overview_rows = (
            self.html_row("Mode", str(plan.get("mode", self.ui_state.mode)).capitalize())
            + self.html_row("Customization depth", depth)
            + (self.html_row("Summary", summary) if summary and summary != "n/a" else "")
            + self.html_row("Auto-migrate", str(counts.get("auto_migrate", 0)))
            + self.html_row("Suggest review", str(counts.get("suggest_review", 0)))
            + self.html_row("Manual review", str(counts.get("manual_review", 0)))
            + self.html_row("Excluded", str(counts.get("excluded", 0)))
        )
        overview = self.html_section(
            "🖥️", "Settings Migration Plan",
            f'<table style="width:100%;">{overview_rows}</table>'
        )

        items = plan.get("items", [])
        if items:
            action_color = {"auto_migrate": "#1B5E20", "suggest_review": "#E65100", "manual_review": "#1565C0", "excluded": "#546E7A"}
            action_bg = {"auto_migrate": "#E8F5E9", "suggest_review": "#FFF3E0", "manual_review": "#E3F2FD", "excluded": "#ECEFF1"}
            item_rows = ""
            for item in items:
                action = str(item.get("action", ""))
                label = action.replace("_", " ").capitalize()
                color = action_color.get(action, "#546E7A")
                bg = action_bg.get(action, "#ECEFF1")
                badge = self.html_pill(label, color, bg)
                conf = str(item.get("confidence", ""))
                item_rows += (
                    f'<tr>'
                    f'<td style="padding:3px 10px 3px 0;font-size:13px;color:#0D1929;">{item.get("name", "")}</td>'
                    f'<td style="padding:3px 6px;font-size:13px;">{badge}</td>'
                    f'<td style="padding:3px 0;font-size:12px;color:#90A4AE;">{conf}</td>'
                    f'</tr>'
                )
            items_section = self.html_section(
                "📋", "Selected Items",
                f'<table style="width:100%;">'
                f'<tr><th style="text-align:left;color:#90A4AE;font-size:11px;font-weight:600;padding-bottom:4px;">Setting</th>'
                f'<th style="text-align:left;color:#90A4AE;font-size:11px;font-weight:600;padding-bottom:4px;">Action</th>'
                f'<th style="text-align:left;color:#90A4AE;font-size:11px;font-weight:600;padding-bottom:4px;">Confidence</th></tr>'
                f'{item_rows}</table>'
            )
        else:
            items_section = ""

        self.preview.setHtml(self.html_wrap(overview + items_section))