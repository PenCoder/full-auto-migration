"""Data selection page for choosing the migration scope."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QWidget
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

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "📁",
            "Which files should come with you?",
            "Choose what to bring — documents, photos, music, videos, and more. "
            "You can always adjust this later if you're not sure.",
        ))

        question = "How would you like to handle your personal files?"
        info = (
            "• <b>Bring everything</b> — all your documents, photos, music, and other files will be copied across.<br>"
            "• <b>Let me choose file types</b> — pick exactly which kinds of files to include (e.g. PDFs, photos, music).<br>"
            "• <b>Recommend based on usage</b> — we look at which files you use most and suggest what to bring.<br>"
            "• <b>Skip for now</b> — move files manually once you're on Linux."
        )

        self.migrate_all_radio = QRadioButton("Bring all my files across")
        self.select_file_types_radio = QRadioButton("Let me choose which types of files to bring (e.g. PDFs, photos, music)")
        self.recommendations_radio = QRadioButton("Recommend what to bring based on how I use my computer")
        self.manual_radio = QRadioButton("I'll move my files myself after the migration")

        guided_panel = self.create_guided_questionnaire(
            question,
            info,
            options=[
                self.migrate_all_radio,
                self.select_file_types_radio,
                self.recommendations_radio,
                self.manual_radio,
            ]
        )
        root.addWidget(guided_panel)

        self.file_types_panel = self._build_file_types_panel()
        root.addWidget(self.file_types_panel)

        self.usage_panel = self._build_usage_panel()
        root.addWidget(self.usage_panel)

        self._sync_radios_from_state()

        self.trust_banner = QLabel()
        self.trust_banner.setObjectName("TrustLabel")
        self.trust_banner.setWordWrap(True)
        self.trust_banner.setAlignment(Qt.AlignCenter)
        root.addWidget(self.trust_banner)

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

    def _build_file_types_panel(self) -> QWidget:
        panel = self.create_guided_questionnaire(
            "Select file types",
            "Choose the file extensions to include when migrating data files.",
            options=[],
        )

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
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
            row = idx // columns
            col = idx % columns
            grid.addWidget(checkbox, row, col)
            self.file_type_checkboxes[ext] = checkbox

        panel.layout().addWidget(container)
        return panel

    def _build_usage_panel(self) -> QWidget:
        panel = self.create_guided_questionnaire(
            "Usage-based recommendations",
            "Recommendations are computed from observed file usage signals on this system (counts and recency).",
            options=[],
        )

        self.refresh_usage_btn = QPushButton("Refresh Usage Recommendations")
        self.refresh_usage_btn.setProperty("role", "primary")
        self.refresh_usage_btn.setFixedWidth(260)
        self.refresh_usage_btn.clicked.connect(self._usage_recommendation_callback)
        panel.layout().addWidget(self.refresh_usage_btn)

        self.usage_summary = QLabel("Run refresh to load file-type usage percentages.")
        self.usage_summary.setObjectName("BodyText")
        self.usage_summary.setWordWrap(True)
        panel.layout().addWidget(self.usage_summary)

        self.activity_view_list = self.activit_list()
        panel.layout().addWidget(self.activity_view_list)

        return panel

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

    def _usage_recommendation_callback(self) -> None:
        if not self.usage_recommendation_cb:
            self.usage_summary.setText("Usage recommendations are not available in this runtime.")
            self.activity_view_list.clear()
            return

        self.refresh_usage_btn.setEnabled(False)
        self.usage_summary.setText("Loading usage recommendations based on local file activity...")
        self.activity_view_list.clear()
        self.usage_recommendation_cb()
        self.refresh_usage_btn.setEnabled(True)

    def _refresh_usage_recommendations(self) -> None:
        recommendations = self.ui_state.usage_recommendations or []
        if not recommendations:
            self.usage_summary.setText("No usage stats available yet. Scanning folders may be needed.")
            self.activity_view_list.clear()
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

        strategy = self.ui_state.data_strategy
        choice_mode = self.ui_state.data_choice_mode

        if mode == "guided":
            self.select_file_types_radio.setEnabled(False)
            self.recommendations_radio.setEnabled(False)
            self.manual_radio.setEnabled(False)
            self.trust_banner.setText(
                "🔒  Guided mode: we'll bring all your files across safely. Nothing is deleted from your Windows machine."
            )
        elif mode == "balanced":
            self.select_file_types_radio.setEnabled(True)
            self.recommendations_radio.setEnabled(True)
            self.manual_radio.setEnabled(True)
            self.trust_banner.setText(
                "🔒  Your files are only copied — never moved or deleted. You can always bring more across later."
            )
        else:
            self.select_file_types_radio.setEnabled(True)
            self.recommendations_radio.setEnabled(True)
            self.manual_radio.setEnabled(True)
            self.trust_banner.setText(
                "🔒  Expert mode: full control over which file types are included in your migration bundle."
            )

        summary_map = {
            "all_files": "Current choice: Migrate all files from supported applications.",
            "selected_types": "Current choice: Migrate selected file types. Configure exact types in Expert Overrides.",
            "ai_recommended": "Current choice: Usage-recommended file migration scope based on local activity signals.",
            "manual": "Current choice: Skip automatic data-file migration and configure manually on Linux.",
        }
        self.choice_summary.setText(summary_map.get(choice_mode, summary_map["all_files"]))

        self.file_types_panel.setVisible(choice_mode == "selected_types")
        self.usage_panel.setVisible(choice_mode == "ai_recommended")

        if choice_mode == "selected_types" and self.file_type_checkboxes:
            for ext, checkbox in self.file_type_checkboxes.items():
                checkbox.setChecked(bool(self.ui_state.selected_file_types.get(ext, checkbox.isChecked())))

        if choice_mode == "ai_recommended" and not self.ui_state.usage_recommendations:
            self._usage_recommendation_callback()
        elif choice_mode == "ai_recommended" and self.ui_state.usage_recommendations:
            self._refresh_usage_recommendations()

        self.next_btn.setEnabled(True)
