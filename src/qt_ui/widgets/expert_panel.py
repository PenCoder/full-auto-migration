from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

from src.config import load_default_config
from src.constants import DATA_DIR
from src.qt_ui.state import QtUiState
from src.services.profile_service import ProfileService


class ExpertPanel(QWidget):
    def __init__(self, ui_state: QtUiState, profile_path: Path | None = None) -> None:
        super().__init__()
        self.ui_state = ui_state
        self.profile_service = ProfileService(profile_path=profile_path)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        tabs = QTabWidget()
        tabs.setObjectName("ExpertTabs")
        self.tabs = tabs

        mapping_tab = QWidget()
        mapping_tab_layout = QVBoxLayout(mapping_tab)
        mapping_tab_layout.setContentsMargins(6, 6, 6, 6)
        mapping_tab_layout.setSpacing(10)

        hardware = QGroupBox("Hardware Advisories")
        hw_form = QFormLayout(hardware)
        for name, confidence in [
            ("NVIDIA GPU", "88%"),
            ("Intel Wi-Fi", "92%"),
            ("Intel BT", "92%"),
        ]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(confidence))
            toggle = QCheckBox("Override")
            row_layout.addWidget(toggle)
            hw_form.addRow(QLabel(name), row)
        mapping_tab_layout.addWidget(hardware)

        mapping_group = QGroupBox("Software Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        self.mapping_table = QTableWidget(0, 5)
        self.mapping_table.setHorizontalHeaderLabels(
            ["Windows", "Package", "Name", "Strategy", "Notes"]
        )
        self.mapping_table.verticalHeader().setVisible(False)
        header = self.mapping_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        self.mapping_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mapping_table.horizontalHeader().setDefaultSectionSize(120)
        self.mapping_table.setMinimumHeight(210)
        self.mapping_table.itemChanged.connect(self._update_confidence_preview)
        mapping_layout.addWidget(self.mapping_table)

        actions_row = QHBoxLayout()
        add_row_btn = QPushButton("Add Mapping")
        add_row_btn.clicked.connect(self._add_mapping_row)
        self.add_row_btn = add_row_btn
        actions_row.addWidget(add_row_btn)

        remove_row_btn = QPushButton("Remove Selected")
        remove_row_btn.clicked.connect(self._remove_selected_mapping_rows)
        self.remove_row_btn = remove_row_btn
        actions_row.addWidget(remove_row_btn)

        load_btn = QPushButton("Load Profile Mappings")
        load_btn.clicked.connect(self._load_mapping_overrides)
        self.load_btn = load_btn
        actions_row.addWidget(load_btn)

        save_btn = QPushButton("Save Profile Mappings")
        save_btn.clicked.connect(self._save_profile)
        self.save_btn = save_btn
        actions_row.addWidget(save_btn)

        scan_btn = QPushButton("Scan Installed Apps")
        scan_btn.clicked.connect(self._scan_installed_apps)
        self.scan_btn = scan_btn
        actions_row.addWidget(scan_btn)

        preview_btn = QPushButton("Preview Confidence")
        preview_btn.clicked.connect(self._update_confidence_preview)
        self.preview_btn = preview_btn
        actions_row.addWidget(preview_btn)
        mapping_layout.addLayout(actions_row)

        self.mapping_status = QLabel("")
        self.mapping_status.setObjectName("BodyText")
        mapping_layout.addWidget(self.mapping_status)

        self.confidence_preview = QLabel("")
        self.confidence_preview.setObjectName("BodyText")
        self.confidence_preview.setWordWrap(True)
        mapping_layout.addWidget(self.confidence_preview)
        mapping_tab_layout.addWidget(mapping_group)
        tabs.addTab(mapping_tab, "Mappings")
        self.mappings_tab_index = 0

        paths_tab = QWidget()
        paths_tab_layout = QVBoxLayout(paths_tab)
        paths_tab_layout.setContentsMargins(6, 6, 6, 6)
        paths_tab_layout.setSpacing(10)

        data_scope = QGroupBox("Data Scope (Used when 'Let Me Choose' is selected)")
        data_layout = QVBoxLayout(data_scope)
        self.folder_checks: dict[str, QCheckBox] = {}
        for name in ["Documents", "Desktop", "Downloads", "Pictures"]:
            box = QCheckBox(name)
            box.setChecked(self.ui_state.selected_folders.get(name, True))
            box.toggled.connect(lambda checked, key=name: self._set_folder(key, checked))
            self.folder_checks[name] = box
            data_layout.addWidget(box)
        paths_tab_layout.addWidget(data_scope)

        custom_group = QGroupBox("Custom Additional Paths")
        custom_layout = QVBoxLayout(custom_group)
        entry_row = QHBoxLayout()
        self.custom_path_input = QLineEdit()
        self.custom_path_input.setPlaceholderText("Enter custom absolute path (e.g. C:/Users/name/Projects)")
        entry_row.addWidget(self.custom_path_input)

        add_custom_btn = QPushButton("Add")
        add_custom_btn.clicked.connect(self._add_custom_path)
        entry_row.addWidget(add_custom_btn)

        browse_custom_btn = QPushButton("Browse")
        browse_custom_btn.clicked.connect(self._browse_custom_path)
        entry_row.addWidget(browse_custom_btn)
        custom_layout.addLayout(entry_row)

        self.custom_paths_list = QListWidget()
        self.custom_paths_list.setMinimumHeight(110)
        custom_layout.addWidget(self.custom_paths_list)

        custom_actions = QHBoxLayout()
        remove_custom_btn = QPushButton("Remove Selected")
        remove_custom_btn.clicked.connect(self._remove_selected_custom_paths)
        custom_actions.addWidget(remove_custom_btn)
        custom_actions.addStretch(1)
        custom_layout.addLayout(custom_actions)

        paths_tab_layout.addWidget(custom_group)
        tabs.addTab(paths_tab, "Paths")
        self.paths_tab_index = 1

        system_tab = QWidget()
        system_tab_layout = QVBoxLayout(system_tab)
        system_tab_layout.setContentsMargins(6, 6, 6, 6)
        system_tab_layout.setSpacing(10)

        distros = QGroupBox("Target Distro Selection")
        distro_layout = QVBoxLayout(distros)
        self.distro_combo = QComboBox()
        self.distro_combo.addItems(["Linux Mint", "Ubuntu", "Fedora", "Debian"])
        self.distro_combo.setCurrentText(self.ui_state.target_distro)
        self.distro_combo.currentTextChanged.connect(self._set_distro)
        distro_layout.addWidget(self.distro_combo)
        system_tab_layout.addWidget(distros)

        advanced = QGroupBox("Advanced Operations")
        advanced_layout = QVBoxLayout(advanced)
        self.incremental = QCheckBox("Incremental Backup")
        self.incremental.setChecked(self.ui_state.advanced_operations.get("incremental_backup", False))
        self.incremental.toggled.connect(lambda v: self._set_op("incremental_backup", v))

        self.parallel = QCheckBox("Parallel Hashing")
        self.parallel.setChecked(self.ui_state.advanced_operations.get("parallel_hashing", False))
        self.parallel.toggled.connect(lambda v: self._set_op("parallel_hashing", v))

        self.rollback = QCheckBox("Create Rollback Point")
        self.rollback.setChecked(self.ui_state.advanced_operations.get("create_rollback_point", False))
        self.rollback.toggled.connect(lambda v: self._set_op("create_rollback_point", v))

        advanced_layout.addWidget(self.incremental)
        advanced_layout.addWidget(self.parallel)
        advanced_layout.addWidget(self.rollback)
        system_tab_layout.addWidget(advanced)
        system_tab_layout.addStretch(1)
        tabs.addTab(system_tab, "System")
        self.system_tab_index = 2

        root.addWidget(tabs)

        root.addStretch(1)
        self._load_mapping_overrides()
        self._load_custom_paths()

    def apply_mode(self, mode: str) -> None:
        is_guided = mode == "guided"
        is_balanced = mode == "balanced"
        is_expert = mode == "expert"

        # Guided mode: no expert edits, read-only presentation.
        if is_guided:
            self.tabs.setCurrentIndex(self.mappings_tab_index)
            self.tabs.setTabEnabled(self.paths_tab_index, False)
            self.tabs.setTabEnabled(self.system_tab_index, False)
            self.add_row_btn.setEnabled(False)
            self.remove_row_btn.setEnabled(False)
            self.scan_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.preview_btn.setEnabled(True)
            self.load_btn.setEnabled(True)
            return

        # Balanced mode: mappings/paths enabled, system-level toggles hidden.
        if is_balanced:
            self.tabs.setTabEnabled(self.paths_tab_index, True)
            self.tabs.setTabEnabled(self.system_tab_index, False)
            self.add_row_btn.setEnabled(True)
            self.remove_row_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            self.load_btn.setEnabled(True)
            if self.tabs.currentIndex() == self.system_tab_index:
                self.tabs.setCurrentIndex(self.mappings_tab_index)
            return

        # Expert mode: full controls available.
        if is_expert:
            self.tabs.setTabEnabled(self.paths_tab_index, True)
            self.tabs.setTabEnabled(self.system_tab_index, True)
            self.add_row_btn.setEnabled(True)
            self.remove_row_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            self.load_btn.setEnabled(True)

    def _set_distro(self, value: str) -> None:
        self.ui_state.target_distro = value

    def _set_op(self, key: str, value: bool) -> None:
        self.ui_state.advanced_operations[key] = value

    def _set_folder(self, key: str, value: bool) -> None:
        self.ui_state.selected_folders[key] = value

    def _add_mapping_row(self) -> None:
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
        for col in range(self.mapping_table.columnCount()):
            self.mapping_table.setItem(row, col, QTableWidgetItem(""))

    def _remove_selected_mapping_rows(self) -> None:
        selected_rows = sorted({idx.row() for idx in self.mapping_table.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            self.mapping_table.removeRow(row)
        self.mapping_status.setText(f"Removed {len(selected_rows)} row(s).")

    def _load_mapping_overrides(self) -> None:
        overrides = self.profile_service.get_mapping_overrides()
        self.mapping_table.blockSignals(True)
        self.mapping_table.setRowCount(0)
        for item in overrides:
            row = self.mapping_table.rowCount()
            self.mapping_table.insertRow(row)
            self.mapping_table.setItem(row, 0, QTableWidgetItem(item.get("windows_name", "")))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(item.get("linux_package", "")))
            self.mapping_table.setItem(row, 2, QTableWidgetItem(item.get("linux_display_name", "")))
            self.mapping_table.setItem(row, 3, QTableWidgetItem(item.get("migration_strategy", "manual")))
            self.mapping_table.setItem(row, 4, QTableWidgetItem(item.get("notes", "")))
        self.mapping_table.blockSignals(False)
        self.mapping_status.setText(f"Loaded {len(overrides)} profile mapping override(s).")
        self._update_confidence_preview()

        profile = self.profile_service.load()
        self.ui_state.target_distro = profile.get("target_distro", self.ui_state.target_distro)
        if hasattr(self, "distro_combo"):
            self.distro_combo.setCurrentText(self.ui_state.target_distro)
        selected = profile.get("selected_folders", {})
        if isinstance(selected, dict) and hasattr(self, "folder_checks"):
            for key, checkbox in self.folder_checks.items():
                checkbox.setChecked(bool(selected.get(key, checkbox.isChecked())))
        ops = profile.get("advanced_operations", {})
        if isinstance(ops, dict) and hasattr(self, "incremental") and hasattr(self, "parallel") and hasattr(self, "rollback"):
            self.incremental.setChecked(bool(ops.get("incremental_backup", self.incremental.isChecked())))
            self.parallel.setChecked(bool(ops.get("parallel_hashing", self.parallel.isChecked())))
            self.rollback.setChecked(bool(ops.get("create_rollback_point", self.rollback.isChecked())))

    def _collect_mapping_overrides(self) -> list[dict[str, str]]:
        overrides: list[dict[str, str]] = []
        for row in range(self.mapping_table.rowCount()):
            windows_name = self._cell_value(row, 0)
            linux_package = self._cell_value(row, 1)
            linux_display_name = self._cell_value(row, 2)
            strategy = self._cell_value(row, 3) or "manual"
            notes = self._cell_value(row, 4)

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
        path = self.profile_service.save(profile)
        self.mapping_status.setText(
            f"Saved {len(profile['mapping_overrides'])} mapping override(s) to {path.name}."
        )
        self._update_confidence_preview()

    def _load_custom_paths(self) -> None:
        profile = self.profile_service.load()
        custom = profile.get("custom_paths", self.ui_state.custom_paths)
        if isinstance(custom, list):
            self.ui_state.custom_paths = [str(p).strip() for p in custom if str(p).strip()]
        self.custom_paths_list.clear()
        for p in self.ui_state.custom_paths:
            self.custom_paths_list.addItem(QListWidgetItem(p))

    def _add_custom_path(self) -> None:
        path = self.custom_path_input.text().strip()
        if not path:
            return
        if path in self.ui_state.custom_paths:
            self.mapping_status.setText("Custom path already exists.")
            return
        self.ui_state.custom_paths.append(path)
        self.custom_paths_list.addItem(QListWidgetItem(path))
        self.custom_path_input.clear()
        self.mapping_status.setText(f"Added custom path: {path}")

    def _browse_custom_path(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Additional Custom Path")
        if not selected:
            return
        self.custom_path_input.setText(selected)
        self._add_custom_path()

    def _remove_selected_custom_paths(self) -> None:
        rows = sorted({idx.row() for idx in self.custom_paths_list.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for row in rows:
            item = self.custom_paths_list.takeItem(row)
            if item is not None and item.text() in self.ui_state.custom_paths:
                self.ui_state.custom_paths.remove(item.text())
        self.mapping_status.setText(f"Removed {len(rows)} custom path(s).")

    def _scan_installed_apps(self) -> None:
        inventory_path = self._resolve_software_inventory_path()
        if inventory_path is None or not inventory_path.exists():
            self.mapping_status.setText(
                "No software inventory found. Run the Windows Scan step first to generate software_inventory.json."
            )
            return

        try:
            data = json.loads(inventory_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.mapping_status.setText(f"Failed to read inventory: {exc}")
            return

        entries = data.get("entries", []) if isinstance(data, dict) else []
        names = []
        for item in entries:
            name = str(item.get("DisplayName", "")).strip()
            if name:
                names.append(name)

        unique = sorted(set(names), key=lambda v: v.lower())
        existing = {
            self._cell_value(row, 0).strip().lower()
            for row in range(self.mapping_table.rowCount())
            if self._cell_value(row, 0).strip()
        }

        added = 0
        self.mapping_table.blockSignals(True)
        for app in unique:
            if app.lower() in existing:
                continue
            row = self.mapping_table.rowCount()
            self.mapping_table.insertRow(row)
            self.mapping_table.setItem(row, 0, QTableWidgetItem(app))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(""))
            self.mapping_table.setItem(row, 2, QTableWidgetItem(""))
            self.mapping_table.setItem(row, 3, QTableWidgetItem("manual"))
            self.mapping_table.setItem(row, 4, QTableWidgetItem("Detected from inventory"))
            added += 1
        self.mapping_table.blockSignals(False)
        self._update_confidence_preview()
        self.mapping_status.setText(
            f"Scanned installed apps from {inventory_path.name}. Added {added} new mapping row(s)."
        )

    def _resolve_software_inventory_path(self) -> Path | None:
        try:
            cfg = load_default_config()
            candidate = DATA_DIR / cfg.source_system.inventory_output_dir / "software_inventory.json"
            if candidate.exists():
                return candidate
        except Exception:
            pass

        matches = list(DATA_DIR.rglob("software_inventory.json"))
        if matches:
            return matches[0]
        return None

    def _update_confidence_preview(self, _item: QTableWidgetItem | None = None) -> None:
        overrides = self._collect_mapping_overrides()
        if not overrides:
            self.confidence_preview.setText(
                "Confidence preview: no active overrides. Default dynamic mappings will be used."
            )
            return

        high = 0
        medium = 0
        low = 0
        for item in overrides:
            strategy = item.get("migration_strategy", "manual").strip().lower()
            if strategy in {"apt", "dnf", "pacman"}:
                high += 1
            elif strategy in {"install linux equivalent", "manual install"}:
                medium += 1
            else:
                low += 1

        total = len(overrides)
        score = int(((high * 1.0) + (medium * 0.7) + (low * 0.4)) / total * 100)
        self.confidence_preview.setText(
            "Confidence preview: "
            f"{score}% overall ({high} high, {medium} medium, {low} low confidence override(s))."
        )

    def _cell_value(self, row: int, col: int) -> str:
        item = self.mapping_table.item(row, col)
        return item.text().strip() if item else ""
