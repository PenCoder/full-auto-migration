"""Summary page for displaying the current migration configuration."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout

from src.qt_ui.pages.base_page import BasePage


class SummaryPage(BasePage):
    """Show a compact snapshot of the current migration choices."""

    def __init__(self, ui_state) -> None:
        super().__init__(ui_state)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(14)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-size: 16px;")
        root.addWidget(self.summary)

        note = QLabel(
            "This summary demonstrates simple flow + optional expert overrides. "
            "Next step is integrating each Qt page with existing migration services."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.request_back.emit)
        root.addWidget(back_btn)

    def refresh(self) -> None:
        strategy_text = "Keep Them All" if self.ui_state.data_strategy == "keep_all" else "Let Me Choose"
        ops = self.ui_state.advanced_operations
        ops_text = (
            f"incremental_backup={ops.get('incremental_backup', False)}, "
            f"parallel_hashing={ops.get('parallel_hashing', False)}, "
            f"create_rollback_point={ops.get('create_rollback_point', False)}"
        )
        exec_text = (
            f"inventory={self.ui_state.inventory_completed}, "
            f"analysis={self.ui_state.analysis_completed}, "
            f"backup={self.ui_state.backup_completed}"
        )
        self.summary.setText(
            f"Mode: {self.ui_state.mode}\n"
            f"Data strategy: {strategy_text}\n"
            f"Target distro: {self.ui_state.target_distro}\n"
            f"Execution: {exec_text}\n"
            f"Advanced operations: {ops_text}\n"
            f"Last error: {self.ui_state.last_error or 'None'}"
        )
