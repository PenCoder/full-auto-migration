from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QtUiState:
    mode: str = "guided"
    expert_panel_visible: bool = False
    target_distro: str = "Linux Mint"
    data_strategy: str = "keep_all"
    data_choice_mode: str = "all_files"
    recommendation_strategy: str = "migrate_all"
    mapping_choice_mode: str = "migrate_all_supported"
    selected_folders: dict[str, bool] = field(
        default_factory=lambda: {
            "Documents": True,
            "Desktop": True,
            "Downloads": True,
            "Pictures": True,
        }
    )
    selected_file_types: dict[str, bool] = field(default_factory=dict)
    usage_recommendations: list[dict[str, object]] = field(default_factory=list)
    custom_paths: list[str] = field(default_factory=list)
    inventory_completed: bool = False
    settings_completed: bool = False
    settings_migration_enabled: bool = True
    analysis_completed: bool = False
    backup_completed: bool = False
    backup_usb_path: str = ""
    bundle_archive_path: str = ""
    restore_completed: bool = False
    verification_completed: bool = False
    total_sovereignty_score: int = 0
    restored_data_size_label: str = ""
    settings_inventory: dict[str, object] = field(default_factory=dict)
    shortcuts_inventory: dict[str, object] = field(default_factory=dict)
    settings_migration_plan: dict[str, object] = field(default_factory=dict)
    settings_selected_items: dict[str, bool] = field(
        default_factory=lambda: {
            "wallpaper": True,
            "theme": True,
            "light_dark": True,
            "accent_color": True,
            "taskbar_layout": True,
            "keyboard_shortcuts": False,
            "file_associations": False,
        }
    )
    is_scanning: bool = False
    last_error: str = ""
    advanced_operations: dict[str, bool] = field(
        default_factory=lambda: {
            "dry_run": False,
        }
    )
