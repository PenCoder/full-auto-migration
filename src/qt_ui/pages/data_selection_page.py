"""Data selection page for choosing the migration scope."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout, QWidget
from src.qt_ui.pages.base_page import BasePage


class DataSelectionPage(BasePage):
    """Let the user choose how files and data should be migrated."""

    def __init__(
        self,
        ui_state,
        current_step: int = 1,
        step_names: list[str] | None = None,
        file_type_catalog: dict[str, bool] | None = None,
        file_type_labels: dict[str, str] | None = None,
        usage_recommendation_cb: Callable[[], list[dict[str, object]]] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self.file_type_catalog = dict(file_type_catalog or {})
        self.file_type_labels = dict(file_type_labels or {})
        self.usage_recommendation_cb = usage_recommendation_cb
        self.file_type_checkboxes: dict[str, QCheckBox] = {}
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._usage_recommendation_callback)
        self._build_ui()
        self.refresh()

    @staticmethod
    def _humanize_file_type_label(ext: str) -> str:
        ext = str(ext).strip().lower()
        fallback_map = {
            ".doc": "Word document files",
            ".docx": "Word document files",
            ".pdf": "PDF files",
            ".mp3": "MP3 audio files",
            ".wav": "WAV audio files",
            ".flac": "FLAC audio files",
            ".aac": "AAC audio files",
            ".jpg": "JPEG image files",
            ".jpeg": "JPEG image files",
            ".png": "PNG image files",
            ".gif": "GIF image files",
            ".bmp": "Bitmap image files",
            ".webp": "WebP image files",
            ".svg": "SVG image files",
            ".ppt": "PowerPoint presentation files",
            ".pptx": "PowerPoint presentation files",
            ".xls": "Excel spreadsheet files",
            ".xlsx": "Excel spreadsheet files",
            ".csv": "CSV files",
            ".zip": "ZIP archive files",
            ".rar": "RAR archive files",
            ".7z": "7-Zip archive files",
            ".tar": "TAR archive files",
            ".gz": "GZip archive files",
            ".json": "JSON files",
            ".xml": "XML files",
            ".yaml": "YAML files",
            ".yml": "YAML files",
            ".ini": "INI configuration files",
            ".html": "HTML files",
            ".css": "CSS files",
            ".js": "JavaScript files",
            ".ts": "TypeScript files",
            ".py": "Python files",
            ".sql": "SQL files",
            ".txt": "Text files",
            ".md": "Markdown files",
            ".rtf": "Rich text files",
            ".mp4": "MP4 video files",
            ".mkv": "Matroska video files",
            ".mov": "MOV video files",
            ".avi": "AVI video files",
            ".log": "Log files",
        }
        return fallback_map.get(ext, f"{ext.lstrip('.').upper()} files" if ext else "Files")

    def _format_file_type_label(self, ext: str) -> str:
        label = self.file_type_labels.get(ext) or self._humanize_file_type_label(ext)
        return f"{label} ({ext})"

    def _build_collapsible_section(self, title: str, body: QWidget) -> QWidget:
        """Wrap a widget in a collapsible section with a toggle button, collapsed by default."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        toggle_btn = QPushButton(f"▶  {title}")
        toggle_btn.setProperty("role", "badge")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(False)
        body.setVisible(False)

        def _on_toggle(checked: bool) -> None:
            body.setVisible(checked)
            toggle_btn.setText(f"{'▼' if checked else '▶'}  {title}")

        toggle_btn.toggled.connect(_on_toggle)
        layout.addWidget(toggle_btn)
        layout.addWidget(body)
        return container

    def _build_file_types_body(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(8, 6, 0, 4)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        file_types = list(self.file_type_catalog.keys())
        if not file_types:
            file_types = [".pdf", ".docx", ".xlsx", ".pptx", ".jpg", ".png", ".mp3", ".mp4", ".zip"]

        if not self.ui_state.selected_file_types:
            self.ui_state.selected_file_types = dict(self.file_type_catalog or {ext: True for ext in file_types})

        columns = 3
        for idx, ext in enumerate(file_types):
            checkbox = QCheckBox(self._format_file_type_label(ext))
            checkbox.setChecked(bool(self.ui_state.selected_file_types.get(ext, True)))
            checkbox.toggled.connect(lambda checked, key=ext: self._on_file_type_toggled(key, checked))
            row_idx = idx // columns
            col_idx = idx % columns
            grid.addWidget(checkbox, row_idx, col_idx)
            self.file_type_checkboxes[ext] = checkbox

        return container

    def _build_usage_body(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 6, 0, 4)
        layout.setSpacing(6)

        self.usage_summary = QLabel("Analysing your file usage patterns…")
        self.usage_summary.setObjectName("BodyText")
        self.usage_summary.setWordWrap(True)
        layout.addWidget(self.usage_summary)

        self.activity_view_list = self.activit_list()
        layout.addWidget(self.activity_view_list)

        return container

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "📁",
            "Which files should come with you?",
            "Choose what to bring — documents, photos, music, videos, and more. "
            "You can always adjust this later if you're not sure.",
        ))

        self.migrate_all_radio = QRadioButton("Bring all my files across")
        self.select_file_types_radio = QRadioButton("Let me choose which types of files to bring")
        self.recommendations_radio = QRadioButton("Recommend what to bring based on how I use my computer")
        self.manual_radio = QRadioButton("I'll move my files myself after the migration")

        self.radio_panel = self.create_guided_questionnaire(
            "How would you like to handle your personal files?",
            None,
            options=[
                self.migrate_all_radio,
                self.select_file_types_radio,
                self.recommendations_radio,
                self.manual_radio,
            ],
        )
        root.addWidget(self.radio_panel)

        self.file_types_section = self._build_collapsible_section(
            "Select file types",
            self._build_file_types_body(),
        )
        self.file_types_section.setVisible(False)
        root.addWidget(self.file_types_section)

        self.usage_section = self._build_collapsible_section(
            "Usage analysis details",
            self._build_usage_body(),
        )
        self.usage_section.setVisible(False)
        root.addWidget(self.usage_section)

        self._sync_radios_from_state()

        _trust_panel, self._trust_label = self._make_info_panel("")
        root.addWidget(_trust_panel)

        self.choice_summary = QLabel("")
        self.choice_summary.setObjectName("BodyText")
        self.choice_summary.setWordWrap(True)
        self.choice_summary.setAlignment(Qt.AlignCenter)
        root.addWidget(self.choice_summary)

        row = QHBoxLayout()
        root.addLayout(row)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

        self.migrate_all_radio.toggled.connect(lambda checked: self._set_choice_mode("all_files", checked))
        self.select_file_types_radio.toggled.connect(lambda checked: self._set_choice_mode("selected_types", checked))
        self.recommendations_radio.toggled.connect(lambda checked: self._set_choice_mode("ai_recommended", checked))
        self.manual_radio.toggled.connect(lambda checked: self._set_choice_mode("manual", checked))

    def _set_strategy(self, strategy: str) -> None:
        self.ui_state.data_strategy = strategy
        self.refresh()

    def _set_choice_mode(self, mode: str, checked: bool) -> None:
        if not checked:
            return
        self.ui_state.data_choice_mode = mode
        if mode == "all_files":
            self.ui_state.data_strategy = "keep_all"
        else:
            self.ui_state.data_strategy = "let_me_choose"
        if mode == "ai_recommended" and not self.ui_state.usage_recommendations:
            self._usage_recommendation_callback()
        self.refresh()

    def _on_file_type_toggled(self, ext: str, checked: bool) -> None:
        self.ui_state.selected_file_types[ext] = checked
        selected_count = sum(1 for enabled in self.ui_state.selected_file_types.values() if enabled)
        total_count = len(self.ui_state.selected_file_types)
        self.choice_summary.setText(
            f"Current choice: Migrate selected file types ({selected_count}/{total_count} enabled)."
        )
        if self.ui_state.data_choice_mode == "ai_recommended":
            self._debounce_timer.start(500)

    def _usage_recommendation_callback(self) -> None:
        if not self.usage_recommendation_cb:
            self.usage_summary.setText("Usage recommendations are not available in this runtime.")
            self.activity_view_list.clear()
            return

        self.set_scanning(True)
        self.usage_summary.setText("Analysing your file usage patterns…")
        self.activity_view_list.clear()
        self.usage_recommendation_cb()

    def _refresh_usage_recommendations(self) -> None:
        self.set_scanning(False)
        self.activity_view_list.clear()
        recommendations = self.ui_state.usage_recommendations or []
        if not recommendations:
            self.usage_summary.setText("No usage stats available yet. Scanning folders may be needed.")
            return

        self.usage_summary.setText(
            f"Loaded {len(recommendations)} usage-based file type recommendations from system file activity."
        )
        for item in recommendations[:20]:
            ext = str(item.get("extension", ""))
            usage = float(item.get("usage_percent", 0.0))
            count = int(item.get("count", 0))
            recent = int(item.get("recent_30_days", 0))
            recommended = bool(item.get("recommended", False))
            mark = "*" if recommended else "-"
            list_item = self.checklist_item(
                f"{mark} {ext:8} usage={usage:5.1f}% files={count:4} recent={recent:4}",
                checked=recommended,
            )
            self.activity_view_list.addItem(list_item)

    def _sync_radios_from_state(self) -> None:
        mode = self.ui_state.data_choice_mode
        if mode == "selected_types":
            self.select_file_types_radio.setChecked(True)
        elif mode == "ai_recommended":
            self.recommendations_radio.setChecked(True)
        elif mode == "manual":
            self.manual_radio.setChecked(True)
        else:
            self.migrate_all_radio.setChecked(True)

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided" and self.ui_state.data_strategy != "keep_all":
            self.ui_state.data_strategy = "keep_all"
            self.ui_state.data_choice_mode = "all_files"
            self.migrate_all_radio.setChecked(True)

        choice_mode = self.ui_state.data_choice_mode
        is_guided = mode == "guided"

        # Hide options that don't apply to guided mode; show them otherwise.
        self.select_file_types_radio.setVisible(not is_guided)
        self.recommendations_radio.setVisible(not is_guided)
        self.manual_radio.setVisible(not is_guided)

        if is_guided:
            self._trust_label.setText(
                "Guided mode: all your files will be copied across safely. Nothing is deleted from Windows."
            )
        elif mode == "balanced":
            self._trust_label.setText(
                "Your files are only copied — never moved or deleted. You can always bring more across later."
            )
        else:
            self._trust_label.setText(
                "Expert mode: full control over which file types are included in your migration bundle."
            )

        summary_map = {
            "all_files": "Current choice: Migrate all files from supported applications.",
            "selected_types": "Current choice: Migrate selected file types. Configure exact types in the Customize panel.",
            "ai_recommended": "Current choice: Usage-recommended file migration scope based on local activity signals.",
            "manual": "Current choice: Skip automatic data-file migration and configure manually on Linux.",
        }
        self.choice_summary.setText(summary_map.get(choice_mode, summary_map["all_files"]))

        self.file_types_section.setVisible(choice_mode == "selected_types")
        self.usage_section.setVisible(choice_mode == "ai_recommended")

        if choice_mode == "selected_types" and self.file_type_checkboxes:
            for ext, checkbox in self.file_type_checkboxes.items():
                checkbox.setChecked(bool(self.ui_state.selected_file_types.get(ext, checkbox.isChecked())))

        if choice_mode == "ai_recommended" and not self.ui_state.usage_recommendations:
            self._usage_recommendation_callback()
        elif choice_mode == "ai_recommended" and self.ui_state.usage_recommendations:
            self._refresh_usage_recommendations()

        self.next_btn.setEnabled(True)
