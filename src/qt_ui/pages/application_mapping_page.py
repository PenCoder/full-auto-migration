from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ApplicationMappingPage(BasePage):
    def __init__(self, ui_state, run_analysis_cb: Callable[[], dict]) -> None:
        super().__init__(ui_state)
        self.run_analysis_cb = run_analysis_cb
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        step = QLabel("Preparation - Step 3 of 4: Application Mapping")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(75)
        self.step_progress.setTextVisible(False)
        self.step_progress.setFixedHeight(10)
        root.addWidget(self.step_progress)

        text = QLabel("Your files are safe. Now, which applications do you want to move?")
        text.setObjectName("HeroTitle")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        root.addWidget(text)

        self.status = QLabel("Run mapping to generate Linux alternatives from detected software.")
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
        self.move_supported_btn.setMinimumHeight(58)
        self.move_supported_btn.setFixedWidth(240)
        self.move_supported_btn.clicked.connect(self._run_mapping)
        row.addWidget(self.move_supported_btn)

        self.configure_btn = QPushButton("Configure Mappings")
        self.configure_btn.setProperty("role", "primary")
        self.configure_btn.setMinimumHeight(58)
        self.configure_btn.setFixedWidth(240)
        self.configure_btn.clicked.connect(self._run_mapping)
        row.addWidget(self.configure_btn)
        root.addLayout(row)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(220)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_mapping(self) -> None:
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
        if result:
            self.ui_state.analysis_completed = True
            self.status.setText("Application mapping completed. Review details in Expert Overrides.")
        else:
            self.status.setText("Mapping finished without results.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Mapping failed: {error}")

    def _on_finished(self) -> None:
        self.move_supported_btn.setEnabled(True)
        self.configure_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        self.next_btn.setEnabled(self.ui_state.analysis_completed or self.ui_state.mode == "expert")
