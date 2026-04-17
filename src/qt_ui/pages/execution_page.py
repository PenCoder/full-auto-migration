from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ExecutionPage(BasePage):
    def __init__(
        self,
        ui_state,
        run_inventory_cb: Callable[[], dict],
        run_analysis_cb: Callable[[], dict],
        run_backup_cb: Callable[[], dict | None],
    ) -> None:
        super().__init__(ui_state)
        self.run_inventory_cb = run_inventory_cb
        self.run_analysis_cb = run_analysis_cb
        self.run_backup_cb = run_backup_cb
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(14)

        title = QLabel("Step 3 of 4: Execute Migration Preparation")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        self.status = QLabel("Run each task below, or use Run All for one-click flow.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        row = QHBoxLayout()
        self.inventory_btn = QPushButton("Run Inventory")
        self.inventory_btn.clicked.connect(self._run_inventory)
        self.analysis_btn = QPushButton("Run Analysis")
        self.analysis_btn.clicked.connect(self._run_analysis)
        self.backup_btn = QPushButton("Run Backup")
        self.backup_btn.clicked.connect(self._run_backup)
        self.all_btn = QPushButton("Run All")
        self.all_btn.clicked.connect(self._run_all)

        row.addWidget(self.inventory_btn)
        row.addWidget(self.analysis_btn)
        row.addWidget(self.backup_btn)
        row.addWidget(self.all_btn)
        root.addLayout(row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Execution output and status updates will appear here.")
        root.addWidget(self.output, stretch=1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.clicked.connect(self.request_next.emit)
        footer.addWidget(self.continue_btn)
        root.addLayout(footer)

    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self.inventory_btn.setEnabled(not busy)
        self.analysis_btn.setEnabled(not busy)
        self.backup_btn.setEnabled(not busy)
        self.all_btn.setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        if msg:
            self.status.setText(msg)

    def _append(self, text: str) -> None:
        self.output.append(text)

    def _run_task(self, task_name: str, fn: Callable[[], object], on_result: Callable[[object], None]) -> None:
        self._set_busy(True, f"{task_name} is running...")
        self._append(f"[START] {task_name}")

        worker = FunctionWorker(fn)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(lambda err: self._on_error(task_name, err))
        worker.signals.finished.connect(lambda: self._set_busy(False, f"{task_name} finished."))
        self.thread_pool.start(worker)

    def _on_error(self, task_name: str, error: str) -> None:
        self.ui_state.last_error = error
        self._append(f"[ERROR] {task_name}: {error}")

    def _run_inventory(self) -> None:
        self._run_task("Inventory", self.run_inventory_cb, self._on_inventory_result)

    def _run_analysis(self) -> None:
        self._run_task("Analysis", self.run_analysis_cb, self._on_analysis_result)

    def _run_backup(self) -> None:
        self._run_task("Backup", self.run_backup_cb, self._on_backup_result)

    def _run_all(self) -> None:
        self._append("[INFO] Run All selected.")
        self._run_task("Inventory", self.run_inventory_cb, self._on_inventory_then_analysis)

    def _on_inventory_then_analysis(self, result: object) -> None:
        self._on_inventory_result(result)
        self._run_task("Analysis", self.run_analysis_cb, self._on_analysis_then_backup)

    def _on_analysis_then_backup(self, result: object) -> None:
        self._on_analysis_result(result)
        self._run_task("Backup", self.run_backup_cb, self._on_backup_result)

    def _on_inventory_result(self, result: object) -> None:
        if result:
            self.ui_state.inventory_completed = True
            self._append("[DONE] Inventory completed successfully.")
        else:
            self._append("[WARN] Inventory returned no data.")
        self.refresh()

    def _on_analysis_result(self, result: object) -> None:
        if result:
            self.ui_state.analysis_completed = True
            self._append("[DONE] Analysis completed successfully.")
        else:
            self._append("[WARN] Analysis returned no data.")
        self.refresh()

    def _on_backup_result(self, result: object) -> None:
        if result:
            self.ui_state.backup_completed = True
            self._append("[DONE] Backup completed successfully.")
        else:
            self._append("[WARN] Backup failed or returned no manifest.")
        self.refresh()

    def refresh(self) -> None:
        parts = [
            f"inventory={self.ui_state.inventory_completed}",
            f"analysis={self.ui_state.analysis_completed}",
            f"backup={self.ui_state.backup_completed}",
        ]
        self.status.setText("Execution status: " + ", ".join(parts))
        self.continue_btn.setEnabled(self.ui_state.backup_completed or self.ui_state.mode == "expert")
