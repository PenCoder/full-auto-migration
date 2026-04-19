from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker
from src.qt_ui.widgets.horizontal_stepper import HorizontalStepper


class ApplicationMappingPage(BasePage):
    def __init__(self, ui_state, run_analysis_cb: Callable[[], dict], current_step: int = 2, step_names: list[str] | None = None) -> None:
        super().__init__(ui_state)
        self.run_analysis_cb = run_analysis_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self.thread_pool = QThreadPool.globalInstance()
        self.is_running = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        text = QLabel(
            "Generate Linux migration recommendations from discovered Windows applications and hardware constraints."
        )
        text.setObjectName("HeroTitle")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        root.addWidget(text)

        self.status = QLabel("Run mapping to produce software_mapping.csv and compatibility advisories.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        row = QHBoxLayout()
        self.move_supported_btn = QPushButton("Move All Supported")
        self.move_supported_btn.setProperty("role", "primary")
        self.move_supported_btn.setMinimumHeight(48)
        self.move_supported_btn.setFixedWidth(220)
        self.move_supported_btn.clicked.connect(self._run_mapping)
        row.addWidget(self.move_supported_btn)

        self.configure_btn = QPushButton("Configure Mappings")
        self.configure_btn.setProperty("role", "primary")
        self.configure_btn.setMinimumHeight(48)
        self.configure_btn.setFixedWidth(220)
        self.configure_btn.clicked.connect(self._run_mapping)
        row.addWidget(self.configure_btn)
        root.addLayout(row)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_mapping(self) -> None:
        self.is_running = True
        self.move_supported_btn.setEnabled(False)
        self.configure_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Generating hardware/software analysis and mapping recommendations...")
        worker = FunctionWorker(self.run_analysis_cb)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.analysis_completed = True
            hw = len(result.get("hardware", []))
            mapped = len(result.get("software", []))
            self.status.setText(
                f"Mapping completed. Generated {hw} hardware advisories and {mapped} software mapping rows."
            )
        else:
            self.status.setText("Mapping finished without results.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Mapping failed.\n{user_facing_error(error)}")

    def _on_finished(self) -> None:
        self.is_running = False
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided":
            self.status.setText(
                "Guided mode uses default compatibility mapping. Run 'Move All Supported' to generate the recommended set."
            )
            self.configure_btn.setEnabled(False)
            self.configure_btn.setVisible(False)
            self.move_supported_btn.setEnabled(not self.is_running)
            self.move_supported_btn.setVisible(True)
        elif mode == "balanced":
            self.status.setText(
                "Balanced mode supports both default mapping and limited customization before generating recommendations."
            )
            self.configure_btn.setVisible(True)
            self.configure_btn.setEnabled(not self.is_running)
            self.move_supported_btn.setVisible(True)
            self.move_supported_btn.setEnabled(not self.is_running)
        else:
            self.status.setText(
                "Expert mode enables full mapping control, including profile overrides and advanced compatibility review."
            )
            self.configure_btn.setVisible(True)
            self.configure_btn.setEnabled(not self.is_running)
            self.move_supported_btn.setVisible(True)
            self.move_supported_btn.setEnabled(not self.is_running)

        self.next_btn.setEnabled(self.ui_state.analysis_completed or self.ui_state.mode == "expert")
