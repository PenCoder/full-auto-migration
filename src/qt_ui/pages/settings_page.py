"""Settings migration page for choosing desktop preferences to carry over."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

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
        ))

        self.status = QLabel("")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.migrate_toggle = QCheckBox("Yes — carry over the Windows look and feel")
        self.migrate_toggle.setChecked(True)
        self.migrate_toggle.toggled.connect(lambda _: self._sync_selections())
        root.addWidget(self.migrate_toggle, alignment=Qt.AlignHCenter)

        self.customize_hint = QLabel(
            "Individual appearance items can be configured in the Customize panel."
        )
        self.customize_hint.setAlignment(Qt.AlignCenter)
        self.customize_hint.setStyleSheet("color: #607D8B; font-size: 11px; font-style: italic;")
        self.customize_hint.setVisible(False)
        root.addWidget(self.customize_hint)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _sync_selections(self) -> None:
        self.ui_state.settings_migration_enabled = self.migrate_toggle.isChecked()

        # Guided mode enforces a fixed minimal selection — user has no panel access.
        if self.ui_state.mode == "guided":
            self.ui_state.settings_selected_items = {
                "wallpaper": True,
                "theme": True,
                "light_dark": False,
                "accent_color": False,
                "taskbar_layout": True,
                "keyboard_shortcuts": False,
                "file_associations": False,
            }

        self._rebuild_plan()

    def _rebuild_plan(self) -> None:
        inventory = self.ui_state.settings_inventory if isinstance(self.ui_state.settings_inventory, dict) else {}
        if inventory:
            self.ui_state.settings_migration_plan = self.settings_service.build_plan(
                inventory,
                self.ui_state.mode,
                selections=self.ui_state.settings_selected_items,
                migrate_enabled=self.ui_state.settings_migration_enabled,
                shortcuts_inventory=self.ui_state.shortcuts_inventory,
            )
        else:
            self.ui_state.settings_migration_plan = {}

    def refresh(self) -> None:
        mode = self.ui_state.mode
        self.migrate_toggle.setChecked(self.ui_state.settings_migration_enabled)
        self.customize_hint.setVisible(mode in ("balanced", "expert"))

        if not self.ui_state.settings_inventory:
            self.status.setText(
                "Complete the scan step first — the current Windows appearance is read during the scan."
            )
        elif mode == "guided":
            self.status.setText(
                "Wallpaper and theme detected. These will be carried across automatically — no action needed."
            )
        elif mode == "balanced":
            self.status.setText(
                "Appearance settings will be carried across. Open the Customize panel to select individual items."
            )
        else:
            self.status.setText(
                "All appearance items available. Configure individual settings in the Customize panel."
            )

        self._sync_selections()
