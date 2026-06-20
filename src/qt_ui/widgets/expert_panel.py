"""Expert override panel for mappings, paths, and advanced options."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

from src.config import load_default_config
from src.constants import DATA_DIR
from src.qt_ui.state import QtUiState
from src.services.profile_service import ProfileService


class ExpertPanel(QWidget):
    """Expert panel with page-specific control layouts using a stacked widget."""

    def __init__(self, ui_state: QtUiState, profile_path: Path | None = None) -> None:
        """Create the expert panel with page-specific tabs."""
        super().__init__()
        self.ui_state = ui_state
        self.profile_service = ProfileService(profile_path=profile_path)
        self.current_mode = ui_state.mode
        self.current_page_key = "mode_selection"
        self.page_widgets: dict[str, QWidget] = {}
        self.on_settings_changed = None  # set by main_window to trigger settings page refresh
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.context_title = QLabel("Expert Configuration")
        self.context_title.setObjectName("StepTitle")
        root.addWidget(self.context_title)

        self.context_description = QLabel("")
        self.context_description.setObjectName("BodyText")
        self.context_description.setWordWrap(True)
        root.addWidget(self.context_description)

        # Stacked widget for page-specific controls
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stacked_widget.setObjectName("ExpertStack")
        root.addWidget(self.stacked_widget)

        # Build page-specific panels
        self.page_widgets["mode_selection"] = self._build_mode_selection_panel()
        self.page_widgets["data_selection"] = self._build_data_selection_panel()
        self.page_widgets["application_mapping"] = self._build_application_mapping_panel()
        self.page_widgets["review_recommendations"] = self._build_review_recommendations_panel()
        self.page_widgets["scan"] = self._build_scan_panel()
        self.page_widgets["backup_bundle"] = self._build_backup_bundle_panel()
        self.page_widgets["restore"] = self._build_restore_panel()
        self.page_widgets["verification"] = self._build_verification_panel()
        self.page_widgets["report"] = self._build_report_panel()

        # Add all pages to stacked widget
        for widget in self.page_widgets.values():
            self.stacked_widget.addWidget(widget)

        root.addStretch(1)
        self._load_mapping_overrides()
        self._load_custom_paths()

    def apply_mode(self, mode: str) -> None:
        self.current_mode = mode
        self._apply_mode_restrictions()

    def set_page_context(self, page_key: str) -> None:
        """Switch to the expert panel for the given page."""
        self.current_page_key = page_key
        self._update_page_context()
        self._apply_mode_restrictions()

    def _update_page_context(self) -> None:
        """Update context title, description, and show the correct page widget."""
        context_map = {
            "mode_selection": {
                "title": "Mode Selection",
                "description": "Configure target distro and system-level operations.",
            },
            "data_selection": {
                "title": "Data Selection",
                "description": "Customize folder scope and additional paths to include in the migration.",
            },
            "application_mapping": {
                "title": "Application Mapping",
                "description": "Tune app mappings and hardware advisories for Linux equivalents.",
            },
            "review_recommendations": {
                "title": "Recommendation Review",
                "description": "Refine mapping overrides and migration scope before bundling.",
            },
            "scan": {
                "title": "Scan",
                "description": "Adjust mapping overrides, target distro, and which appearance/settings items to migrate.",
            },
            "backup_bundle": {
                "title": "Backup",
                "description": "Finalize data scope and backup operations before generating the bundle.",
            },
            "restore": {
                "title": "Restore",
                "description": "Adjust target-system behavior and advanced operations for restoration.",
            },
            "verification": {
                "title": "Verification",
                "description": "Review verification results; adjust system settings if needed.",
            },
            "report": {
                "title": "Final Report",
                "description": "Review the migration report. Expert controls are minimized at this stage.",
            },
        }

        cfg = context_map.get(self.current_page_key, context_map["mode_selection"])
        self.context_title.setText(cfg["title"])
        self.context_description.setText(cfg["description"])

        # Switch to the appropriate page widget
        if self.current_page_key in self.page_widgets:
            index = list(self.page_widgets.keys()).index(self.current_page_key)
            self.stacked_widget.setCurrentIndex(index)

    def _build_mode_selection_panel(self) -> QWidget:
        """Expert controls for mode selection page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        self.mode_sim_group = QGroupBox("Simulation")
        sim_group = self.mode_sim_group
        sim_form = QFormLayout(sim_group)
        sim_form.setSpacing(10)

        self.mode_dry_run = QCheckBox("Simulation Mode (Dry Run)")
        self.mode_dry_run.setToolTip("Test migration without writing any data to disk.")
        self.mode_dry_run.setChecked(self.ui_state.advanced_operations.get("dry_run", False))
        self.mode_dry_run.toggled.connect(lambda v: self._set_op("dry_run", v))

        dry_run_info = QLabel(
            "When enabled, the tool scans your files and generates a full manifest "
            "showing exactly what would be backed up — but nothing is written to disk. "
            "Use this to preview the migration before committing."
        )
        dry_run_info.setWordWrap(True)
        dry_run_info.setStyleSheet("color: #546E7A; font-size: 13px;")

        sim_form.addRow(self.mode_dry_run)
        sim_form.addRow(dry_run_info)
        layout.addWidget(sim_group)
        layout.addStretch(1)
        return widget

    def _build_settings_migration_controls(self, layout: QVBoxLayout) -> None:
        """Append target-distro and appearance-item controls to an existing layout.

        Folded into the scan panel since settings migration no longer has its
        own wizard page — these controls are reached via the scan page's
        Customize context instead.
        """
        distro_group = QGroupBox("Target Distro")
        distro_layout = QVBoxLayout(distro_group)
        self.settings_distro_combo = QComboBox()
        self.settings_distro_combo.addItems(["Linux Mint"])
        self.settings_distro_combo.setCurrentText(self.ui_state.target_distro)
        self.settings_distro_combo.currentTextChanged.connect(self._set_distro)
        self.settings_distro_combo.setEnabled(False)
        distro_layout.addWidget(self.settings_distro_combo)
        layout.addWidget(distro_group)

        appearance_group = QGroupBox("Appearance Items")
        appearance_form = QFormLayout(appearance_group)
        appearance_form.setSpacing(8)

        self.settings_appearance_checkboxes: dict[str, QCheckBox] = {}
        _base_items = [
            ("wallpaper", "Wallpaper"),
            ("theme", "Theme file"),
            ("light_dark", "Light / Dark preference"),
            ("accent_color", "Accent color"),
        ]
        _expert_only_items = [
            ("taskbar_layout", "App shortcuts (Desktop, Start Menu, Taskbar)"),
            ("keyboard_shortcuts", "Keyboard shortcuts"),
            ("file_associations", "File associations"),
        ]
        for key, label in _base_items + _expert_only_items:
            cb = QCheckBox(label)
            cb.setChecked(self.ui_state.settings_selected_items.get(key, False))
            cb.toggled.connect(lambda v, k=key: self._set_appearance(k, v))
            appearance_form.addRow(cb)
            self.settings_appearance_checkboxes[key] = cb

        layout.addWidget(appearance_group)

        self.settings_expert_checks = [
            self.settings_appearance_checkboxes[k]
            for k in ("taskbar_layout", "keyboard_shortcuts", "file_associations")
        ]

    def _build_data_selection_panel(self) -> QWidget:
        """Expert controls for data selection page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # --- Conflict & Sanitation Group ---
        filter_group = QGroupBox("Filter & Conflict Strategy")
        filter_form = QFormLayout(filter_group)

        self.data_conflict_strategy = QComboBox()
        self.data_conflict_strategy.addItems(["Rename (Keep Both)", "Overwrite", "Skip Existing"])
        
        self.data_exclude_regex = QLineEdit()
        self.data_exclude_regex.setPlaceholderText("e.g. node_modules; *.tmp; .git")
        
        self.data_sanitize_names = QCheckBox("Sanitize Windows Filenames")
        self.data_sanitize_names.setToolTip("Removes characters like ':', '?', '*' which are illegal on some Linux filesystems.")
        self.data_sanitize_names.setChecked(True)

        filter_form.addRow("On Conflict:", self.data_conflict_strategy)
        filter_form.addRow("Exclusions:", self.data_exclude_regex)
        filter_form.addRow(self.data_sanitize_names)
        layout.addWidget(filter_group)

        custom_group = QGroupBox("Custom Additional Paths")
        custom_layout = QVBoxLayout(custom_group)
        entry_row = QHBoxLayout()
        self.data_custom_path_input = QLineEdit()
        self.data_custom_path_input.setPlaceholderText("Enter custom path...")
        entry_row.addWidget(self.data_custom_path_input)

        add_custom_btn = QPushButton("Add")
        add_custom_btn.clicked.connect(self._add_custom_path)
        entry_row.addWidget(add_custom_btn)

        browse_custom_btn = QPushButton("Browse")
        browse_custom_btn.clicked.connect(self._browse_custom_path)
        entry_row.addWidget(browse_custom_btn)
        custom_layout.addLayout(entry_row)

        self.data_custom_paths_list = QListWidget()
        self.data_custom_paths_list.setMinimumHeight(110)
        custom_layout.addWidget(self.data_custom_paths_list)

        custom_actions = QHBoxLayout()
        remove_custom_btn = QPushButton("Remove Selected")
        remove_custom_btn.clicked.connect(self._remove_selected_custom_paths)
        custom_actions.addWidget(remove_custom_btn)
        custom_actions.addStretch(1)
        custom_layout.addLayout(custom_actions)

        layout.addWidget(custom_group)
        layout.addStretch(1)
        return widget

    def _build_application_mapping_panel(self) -> QWidget:
        """Expert controls for application mapping page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # --- Compatibility & Strategy ---
        strategy_group = QGroupBox("Installation Strategy")
        strat_layout = QHBoxLayout(strategy_group)

        self.app_pkg_pref = QComboBox()
        self.app_pkg_pref.addItems(["Prefer Native (.deb/.rpm)", "Prefer Flatpak", "Prefer Snap"])
        
        self.app_auto_wine = QCheckBox("Auto-Wine Prefix")
        self.app_auto_wine.setToolTip("Create a Wine bottle for apps without a native Linux version.")

        strat_layout.addWidget(QLabel("Package Type:"))
        strat_layout.addWidget(self.app_pkg_pref)
        strat_layout.addWidget(self.app_auto_wine)
        layout.addWidget(strategy_group)

        mapping_group = QGroupBox("Software Mappings")
        mapping_layout = QVBoxLayout(mapping_group)

        # Scrollable area for mappings
        self.app_mappings_scroll = QScrollArea()
        self.app_mappings_scroll.setWidgetResizable(True)
        self.app_mappings_scroll.setMinimumHeight(210)
        self.app_mappings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_mappings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.app_mappings_container = QWidget()
        self.app_mappings_layout = QVBoxLayout(self.app_mappings_container)
        self.app_mappings_layout.setSpacing(10)

        self.app_mappings_scroll.setWidget(self.app_mappings_container)
        mapping_layout.addWidget(self.app_mappings_scroll)

        actions_row = QHBoxLayout()
        self.app_add_row_btn = QPushButton("Add Mapping")
        self.app_add_row_btn.clicked.connect(self._add_mapping_row)
        actions_row.addWidget(self.app_add_row_btn)

        self.app_remove_row_btn = QPushButton("Remove Selected")
        self.app_remove_row_btn.clicked.connect(self._remove_selected_mapping_rows)
        actions_row.addWidget(self.app_remove_row_btn)

        # self.app_load_btn = QPushButton("Load Profile")
        # self.app_load_btn.clicked.connect(self._load_mapping_overrides)
        # actions_row.addWidget(self.app_load_btn)

        self.app_save_btn = QPushButton("Save Profile")
        self.app_save_btn.clicked.connect(self._save_profile)
        actions_row.addWidget(self.app_save_btn)

        self.app_scan_btn = QPushButton("Scan Apps")
        self.app_scan_btn.clicked.connect(self._scan_installed_apps)
        actions_row.addWidget(self.app_scan_btn)
        mapping_layout.addLayout(actions_row)

        self.app_mapping_status = QLabel("")
        self.app_mapping_status.setObjectName("BodyText")
        mapping_layout.addWidget(self.app_mapping_status)

        self.app_confidence_preview = QLabel("")
        self.app_confidence_preview.setObjectName("BodyText")
        self.app_confidence_preview.setWordWrap(True)
        mapping_layout.addWidget(self.app_confidence_preview)

        layout.addWidget(mapping_group)
        return widget

    def _build_review_recommendations_panel(self) -> QWidget:
        """Expert controls for review recommendations page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        mapping_group = QGroupBox("Software Mapping Overrides")
        mapping_layout = QVBoxLayout(mapping_group)

        # Scrollable area for mappings
        self.review_mappings_scroll = QScrollArea()
        self.review_mappings_scroll.setWidgetResizable(True)
        self.review_mappings_scroll.setMinimumHeight(200)
        self.review_mappings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.review_mappings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.review_mappings_container = QWidget()
        self.review_mappings_layout = QVBoxLayout(self.review_mappings_container)
        self.review_mappings_layout.setSpacing(10)

        self.review_mappings_scroll.setWidget(self.review_mappings_container)
        mapping_layout.addWidget(self.review_mappings_scroll)

        actions_row = QHBoxLayout()
        self.review_add_btn = QPushButton("Add")
        self.review_add_btn.clicked.connect(self._add_mapping_row)
        actions_row.addWidget(self.review_add_btn)

        self.review_remove_btn = QPushButton("Remove Selected")
        self.review_remove_btn.clicked.connect(self._remove_selected_mapping_rows)
        actions_row.addWidget(self.review_remove_btn)
        mapping_layout.addLayout(actions_row)
        layout.addWidget(mapping_group)

        data_scope_group = QGroupBox("Data Scope")
        data_layout = QVBoxLayout(data_scope_group)
        self.review_folder_checks: dict[str, QCheckBox] = {}
        for name in ["Documents", "Desktop", "Downloads", "Pictures"]:
            box = QCheckBox(name)
            box.setChecked(self.ui_state.selected_folders.get(name, True))
            box.toggled.connect(lambda checked, key=name: self._set_folder(key, checked))
            self.review_folder_checks[name] = box
            data_layout.addWidget(box)
        layout.addWidget(data_scope_group)

        layout.addStretch(1)
        return widget

    def _build_scan_panel(self) -> QWidget:
        """Expert controls for scan page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        mapping_group = QGroupBox("Mapping Overrides")
        mapping_layout = QVBoxLayout(mapping_group)

        # Scrollable area for mappings
        self.scan_mappings_scroll = QScrollArea()
        self.scan_mappings_scroll.setWidgetResizable(True)
        self.scan_mappings_scroll.setMinimumHeight(150)
        self.scan_mappings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scan_mappings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scan_mappings_container = QWidget()
        self.scan_mappings_layout = QVBoxLayout(self.scan_mappings_container)
        self.scan_mappings_layout.setSpacing(10)

        self.scan_mappings_scroll.setWidget(self.scan_mappings_container)
        mapping_layout.addWidget(self.scan_mappings_scroll)

        actions_row = QHBoxLayout()
        self.scan_add_btn = QPushButton("Add")
        self.scan_add_btn.clicked.connect(self._add_mapping_row)
        actions_row.addWidget(self.scan_add_btn)

        self.scan_remove_btn = QPushButton("Remove Selected")
        self.scan_remove_btn.clicked.connect(self._remove_selected_mapping_rows)
        actions_row.addWidget(self.scan_remove_btn)
        mapping_layout.addLayout(actions_row)
        layout.addWidget(mapping_group)

        self._build_settings_migration_controls(layout)

        layout.addStretch(1)
        return widget

    def _build_backup_bundle_panel(self) -> QWidget:
        """Expert controls for backup bundle page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        data_scope_group = QGroupBox("Data Scope")
        data_layout = QVBoxLayout(data_scope_group)
        self.backup_folder_checks: dict[str, QCheckBox] = {}
        for name in ["Documents", "Desktop", "Downloads", "Pictures"]:
            box = QCheckBox(name)
            box.setChecked(self.ui_state.selected_folders.get(name, True))
            box.toggled.connect(lambda checked, key=name: self._set_folder(key, checked))
            self.backup_folder_checks[name] = box
            data_layout.addWidget(box)
        layout.addWidget(data_scope_group)

        custom_group = QGroupBox("Custom Paths")
        custom_layout = QVBoxLayout(custom_group)
        entry_row = QHBoxLayout()
        self.backup_custom_path_input = QLineEdit()
        self.backup_custom_path_input.setPlaceholderText("Enter custom path...")
        entry_row.addWidget(self.backup_custom_path_input)

        add_custom_btn = QPushButton("Add")
        add_custom_btn.clicked.connect(self._add_custom_path)
        entry_row.addWidget(add_custom_btn)
        custom_layout.addLayout(entry_row)

        self.backup_custom_paths_list = QListWidget()
        self.backup_custom_paths_list.setMinimumHeight(100)
        custom_layout.addWidget(self.backup_custom_paths_list)

        remove_custom_btn = QPushButton("Remove Selected")
        remove_custom_btn.clicked.connect(self._remove_selected_custom_paths)
        custom_layout.addWidget(remove_custom_btn)
        layout.addWidget(custom_group)

        layout.addStretch(1)
        return widget

    def _build_restore_panel(self) -> QWidget:
        """Expert controls for restore page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        distro_group = QGroupBox("Target Distro")
        distro_layout = QVBoxLayout(distro_group)
        self.restore_distro_combo = QComboBox()
        self.restore_distro_combo.addItems(["Linux Mint"])
        self.restore_distro_combo.setCurrentText(self.ui_state.target_distro)
        self.restore_distro_combo.currentTextChanged.connect(self._set_distro)
        self.restore_distro_combo.setEnabled(False)
        distro_layout.addWidget(self.restore_distro_combo)
        layout.addWidget(distro_group)

        layout.addStretch(1)
        return widget

    def _build_verification_panel(self) -> QWidget:
        """Expert controls for verification page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        layout.addWidget(QLabel("No additional expert controls for verification."))
        layout.addStretch(1)
        return widget

    def _build_report_panel(self) -> QWidget:
        """Expert controls for report page (minimal)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(QLabel("Report generation is complete. No additional expert controls are available."))
        layout.addStretch(1)
        return widget

    def _apply_mode_restrictions(self) -> None:
        """Hide or show advanced controls based on the active mode."""
        is_expert = self.current_mode == "expert"
        for attr in (
            "mode_dry_run", "mode_sim_group",
            "app_pkg_pref", "app_auto_wine", "app_scan_btn",
            "app_save_btn", "app_add_row_btn", "app_remove_row_btn",
            "data_conflict_strategy", "data_exclude_regex", "data_sanitize_names",
        ):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setVisible(is_expert)
        for cb in getattr(self, "settings_expert_checks", []):
            cb.setVisible(is_expert)

    def _set_distro(self, value: str) -> None:
        self.ui_state.target_distro = value

    def _set_op(self, key: str, value: bool) -> None:
        self.ui_state.advanced_operations[key] = value

    def _set_appearance(self, key: str, value: bool) -> None:
        self.ui_state.settings_selected_items[key] = value
        if self.on_settings_changed is not None:
            self.on_settings_changed()

    def _set_folder(self, key: str, value: bool) -> None:
        self.ui_state.selected_folders[key] = value

    def _add_mapping_row(self) -> None:
        layout_map = {
            "application_mapping": getattr(self, "app_mappings_layout", None),
            "review_recommendations": getattr(self, "review_mappings_layout", None),
            "scan": getattr(self, "scan_mappings_layout", None),
        }
        target_layout = layout_map.get(self.current_page_key)
        if target_layout is None:
            return

        last = target_layout.count() - 1
        if last >= 0 and target_layout.itemAt(last).spacerItem():
            target_layout.removeItem(target_layout.itemAt(last))

        empty_item = {
            "windows_name": "",
            "linux_package": "",
            "linux_display_name": "",
            "migration_strategy": "manual",
            "notes": "",
        }
        target_layout.addWidget(self._create_mapping_widget(empty_item))
        target_layout.addStretch(1)

    def _remove_selected_mapping_rows(self) -> None:
        layout_map = {
            "application_mapping": getattr(self, "app_mappings_layout", None),
            "review_recommendations": getattr(self, "review_mappings_layout", None),
            "scan": getattr(self, "scan_mappings_layout", None),
        }
        target_layout = layout_map.get(self.current_page_key)
        if target_layout is None:
            return
        for i in reversed(range(target_layout.count())):
            item = target_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), "windows_edit"):
                w = item.widget()
                target_layout.removeWidget(w)
                w.deleteLater()
                break

    def _load_mapping_overrides(self) -> None:
        overrides = self.profile_service.get_mapping_overrides()

        # Clear existing mapping widgets
        while self.app_mappings_layout.count():
            child = self.app_mappings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for item in overrides:
            mapping_widget = self._create_mapping_widget(item)
            self.app_mappings_layout.addWidget(mapping_widget)

        self.app_mappings_layout.addStretch(1)
        self._update_confidence_preview()

        profile = self.profile_service.load()
        self.ui_state.target_distro = profile.get("target_distro", self.ui_state.target_distro)
        if hasattr(self, "mode_distro_combo"):
            self.mode_distro_combo.setCurrentText(self.ui_state.target_distro)
        if hasattr(self, "settings_distro_combo"):
            self.settings_distro_combo.setCurrentText(self.ui_state.target_distro)

    def _create_mapping_widget(self, item: dict[str, str]) -> QWidget:
        """Create a vertical widget for a single mapping entry."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Windows app name
        windows_layout = QHBoxLayout()
        windows_layout.addWidget(QLabel("Windows:"))
        windows_edit = QLineEdit(item.get("windows_name", ""))
        windows_edit.setPlaceholderText("Windows application name")
        windows_layout.addWidget(windows_edit)
        layout.addLayout(windows_layout)

        # Linux package
        package_layout = QHBoxLayout()
        package_layout.addWidget(QLabel("Package:"))
        package_edit = QLineEdit(item.get("linux_package", ""))
        package_edit.setPlaceholderText("Linux package name")
        package_layout.addWidget(package_edit)
        layout.addLayout(package_layout)

        # Linux display name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_edit = QLineEdit(item.get("linux_display_name", ""))
        name_edit.setPlaceholderText("Display name")
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)

        # Migration strategy
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("Strategy:"))
        strategy_combo = QComboBox()
        strategy_combo.addItems(["manual", "auto", "wine", "flatpak", "snap"])
        strategy_combo.setCurrentText(item.get("migration_strategy", "manual"))
        strategy_layout.addWidget(strategy_combo)
        layout.addLayout(strategy_layout)

        # Notes
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel("Notes:"))
        notes_edit = QLineEdit(item.get("notes", ""))
        notes_edit.setPlaceholderText("Additional notes")
        notes_layout.addWidget(notes_edit)
        layout.addLayout(notes_layout)

        # Remove button
        remove_layout = QHBoxLayout()
        remove_layout.addStretch(1)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_mapping_widget(widget))
        remove_layout.addWidget(remove_btn)
        layout.addLayout(remove_layout)

        # Store references for data collection
        widget.windows_edit = windows_edit
        widget.package_edit = package_edit
        widget.name_edit = name_edit
        widget.strategy_combo = strategy_combo
        widget.notes_edit = notes_edit

        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        return widget

    def _remove_mapping_widget(self, widget: QWidget) -> None:
        """Remove a mapping widget from the layout."""
        self.app_mappings_layout.removeWidget(widget)
        widget.deleteLater()

    def _collect_mapping_overrides(self) -> list[dict[str, str]]:
        overrides: list[dict[str, str]] = []
        for i in range(self.app_mappings_layout.count()):
            item = self.app_mappings_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), 'windows_edit'):
                widget = item.widget()
                windows_name = widget.windows_edit.text().strip()
                linux_package = widget.package_edit.text().strip()
                linux_display_name = widget.name_edit.text().strip()
                strategy = widget.strategy_combo.currentText()
                notes = widget.notes_edit.text().strip()

                if not windows_name or not linux_package:
                    continue

                overrides.append(
                    {
                        "windows_name": windows_name,
                        "linux_package": linux_package,
                        "linux_display_name": linux_display_name or linux_package,
                        "migration_strategy": strategy,
                        "notes": notes,
                    }
                )
        return overrides

    def _save_profile(self) -> None:
        profile = self.profile_service.load()
        profile["mode"] = self.ui_state.mode
        profile["target_distro"] = self.ui_state.target_distro
        profile["selected_folders"] = dict(self.ui_state.selected_folders)
        profile["advanced_operations"] = dict(self.ui_state.advanced_operations)
        profile["custom_paths"] = list(self.ui_state.custom_paths)
        profile["mapping_overrides"] = self._collect_mapping_overrides()
        self.profile_service.save(profile)
        self._update_confidence_preview()

    def _load_custom_paths(self) -> None:
        profile = self.profile_service.load()
        custom = profile.get("custom_paths", self.ui_state.custom_paths)
        if isinstance(custom, list):
            self.ui_state.custom_paths = [str(p).strip() for p in custom if str(p).strip()]

    def _add_custom_path(self) -> None:
        input_field = None
        list_widget = None

        if self.current_page_key == "data_selection":
            input_field = self.data_custom_path_input
            list_widget = self.data_custom_paths_list
        elif self.current_page_key == "backup_bundle":
            input_field = self.backup_custom_path_input
            list_widget = self.backup_custom_paths_list

        if not input_field or not list_widget:
            return

        path = input_field.text().strip()
        if not path or path in self.ui_state.custom_paths:
            return

        self.ui_state.custom_paths.append(path)
        list_widget.addItem(QListWidgetItem(path))
        input_field.clear()

    def _browse_custom_path(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Additional Path")
        if not selected:
            return

        if self.current_page_key == "data_selection":
            self.data_custom_path_input.setText(selected)
        elif self.current_page_key == "backup_bundle":
            self.backup_custom_path_input.setText(selected)

    def _remove_selected_custom_paths(self) -> None:
        list_widget = None
        if self.current_page_key == "data_selection":
            list_widget = self.data_custom_paths_list
        elif self.current_page_key == "backup_bundle":
            list_widget = self.backup_custom_paths_list

        if not list_widget:
            return

        selected_items = list_widget.selectedItems()
        for item in selected_items:
            path = item.text()
            if path in self.ui_state.custom_paths:
                self.ui_state.custom_paths.remove(path)
            list_widget.takeItem(list_widget.row(item))

    def _update_confidence_preview(self) -> None:
        overrides = self._collect_mapping_overrides()
        count = len(overrides)
        label = getattr(self, "app_confidence_preview", None)
        if label is not None:
            label.setText(f"{count} mapping override(s) defined." if count else "No overrides — using default mappings.")

    def _scan_installed_apps(self) -> None:
        status = getattr(self, "app_mapping_status", None)
        if status:
            status.setText("Scanning installed apps…")
        try:
            import winapps
            count = sum(1 for _ in winapps.list_installed())
            if status:
                status.setText(f"Found {count} installed app(s) on this system.")
        except ImportError:
            if status:
                status.setText("App scanning is only available on Windows.")
        except Exception as exc:
            if status:
                status.setText(f"Scan failed: {exc}")
