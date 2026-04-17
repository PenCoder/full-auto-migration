from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.qt_ui.state import QtUiState


class ExpertPanel(QWidget):
    def __init__(self, ui_state: QtUiState) -> None:
        super().__init__()
        self.ui_state = ui_state
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

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
        root.addWidget(hardware)

        mapping_group = QGroupBox("Software Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        table = QTableWidget(3, 3)
        table.setHorizontalHeaderLabels(["Windows", "Linux", "Openness"])
        data = [
            ("Microsoft Office", "LibreOffice", "95% Open"),
            ("Outlook", "Evolution Mail", "95% Open"),
            ("VLC", "VLC", "99% Open"),
        ]
        for row, (w_name, l_name, open_score) in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(w_name))
            table.setItem(row, 1, QTableWidgetItem(l_name))
            table.setItem(row, 2, QTableWidgetItem(open_score))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        mapping_layout.addWidget(table)
        root.addWidget(mapping_group)

        distros = QGroupBox("Target Distro Selection")
        distro_layout = QVBoxLayout(distros)
        self.distro_combo = QComboBox()
        self.distro_combo.addItems(["Linux Mint", "Ubuntu", "Fedora", "Debian"])
        self.distro_combo.setCurrentText(self.ui_state.target_distro)
        self.distro_combo.currentTextChanged.connect(self._set_distro)
        distro_layout.addWidget(self.distro_combo)
        root.addWidget(distros)

        data_scope = QGroupBox("Data Scope (Used when 'Let Me Choose' is selected)")
        data_layout = QVBoxLayout(data_scope)
        self.folder_checks: dict[str, QCheckBox] = {}
        for name in ["Documents", "Desktop", "Downloads", "Pictures"]:
            box = QCheckBox(name)
            box.setChecked(self.ui_state.selected_folders.get(name, True))
            box.toggled.connect(lambda checked, key=name: self._set_folder(key, checked))
            self.folder_checks[name] = box
            data_layout.addWidget(box)
        root.addWidget(data_scope)

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
        root.addWidget(advanced)

        root.addStretch(1)

    def _set_distro(self, value: str) -> None:
        self.ui_state.target_distro = value

    def _set_op(self, key: str, value: bool) -> None:
        self.ui_state.advanced_operations[key] = value

    def _set_folder(self, key: str, value: bool) -> None:
        self.ui_state.selected_folders[key] = value
