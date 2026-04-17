from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout

from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ScanPage(BasePage):
    def __init__(self, ui_state, run_inventory_cb: Callable[[], dict]) -> None:
        super().__init__(ui_state)
        self.run_inventory_cb = run_inventory_cb
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        step = QLabel("Preparation - Step 1 of 4: The Windows Scan")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(25)
        self.step_progress.setTextVisible(False)
        self.step_progress.setFixedHeight(10)
        root.addWidget(self.step_progress)

        text = QLabel(
            "We're going to scan your computer to find your files and applications.\n"
            "Nothing will be moved yet."
        )
        text.setObjectName("HeroTitle")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        root.addWidget(text)

        self.status = QLabel("Press Start Scan to begin inventory.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setProperty("role", "primary")
        self.scan_btn.setMinimumHeight(58)
        self.scan_btn.setFixedWidth(260)
        self.scan_btn.clicked.connect(self._run_scan)
        root.addWidget(self.scan_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(220)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_scan(self) -> None:
        self.scan_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Scanning hardware and software inventory...")
        worker = FunctionWorker(self.run_inventory_cb)
        worker.signals.result.connect(self._on_scan_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_scan_result(self, result: object) -> None:
        if result:
            self.ui_state.inventory_completed = True
            self.status.setText("Scan completed successfully.")
        else:
            self.status.setText("Scan finished but no results were returned.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Scan failed: {error}")
        self.refresh()

    def _on_finished(self) -> None:
        self.scan_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        self.next_btn.setEnabled(self.ui_state.inventory_completed or self.ui_state.mode == "expert")
