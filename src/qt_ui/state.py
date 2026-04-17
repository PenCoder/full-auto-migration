from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QtUiState:
    mode: str = "guided"
    expert_panel_visible: bool = False
    target_distro: str = "Linux Mint"
    data_strategy: str = "keep_all"
    selected_folders: dict[str, bool] = field(
        default_factory=lambda: {
            "Documents": True,
            "Desktop": True,
            "Downloads": True,
            "Pictures": True,
        }
    )
    inventory_completed: bool = False
    analysis_completed: bool = False
    backup_completed: bool = False
    restore_completed: bool = False
    verification_completed: bool = False
    total_sovereignty_score: int = 0
    restored_data_size_label: str = ""
    last_error: str = ""
    advanced_operations: dict[str, bool] = field(
        default_factory=lambda: {
            "incremental_backup": True,
            "parallel_hashing": True,
            "create_rollback_point": False,
        }
    )
