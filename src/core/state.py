"""Centralized state management for the migration workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MigrationPhase(str, Enum):
    """Enumeration of migration workflow phases."""
    MODE_SELECTION = "mode_selection"
    INVENTORY = "inventory"
    ANALYSIS = "analysis"
    RECOMMENDATIONS = "recommendations"
    DATA_SELECTION = "data_selection"
    BACKUP = "backup"
    RESTORE = "restore"
    VERIFICATION = "verification"
    REPORT = "report"


class ActivityLevel(str, Enum):
    """Severity levels for activity log entries."""
    INFO = "info"
    SUCCESS = "done"
    WARNING = "warn"
    ERROR = "fail"


@dataclass
class ActivityEntry:
    """Single activity log entry with timestamp and categorization."""
    timestamp: datetime
    level: ActivityLevel
    phase: MigrationPhase | None
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging/storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "phase": self.phase.value if self.phase else None,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class MigrationState:
    """Centralized single source of truth for all migration workflow state."""

    # --- Runtime Configuration ---
    runtime_mode: str  # "windows" or "linux"
    config: Any  # MigrationConfigRoot (avoid circular import)

    # --- User Preferences ---
    migration_mode: str = "guided"  # "guided", "balanced", "expert"
    target_distro: str = "Linux Mint"
    advanced_operations: dict[str, bool] = field(
        default_factory=lambda: {
            "incremental_backup": True,
            "parallel_hashing": True,
            "create_rollback_point": False,
        }
    )

    # --- Data Selection State ---
    data_choice_mode: str = "all_files"  # "all_files", "selected_types", "ai_recommended", "manual"
    selected_folders: dict[str, bool] = field(
        default_factory=lambda: {
            "Documents": True,
            "Desktop": True,
            "Downloads": True,
            "Pictures": True,
        }
    )
    custom_paths: list[str] = field(default_factory=list)
    selected_file_types: dict[str, bool] = field(default_factory=dict)

    # --- Analysis & Recommendation State ---
    recommendation_strategy: str = "migrate_all"  # "migrate_all" or "prioritize"
    inventory_strategy: str = "quick"  # "quick", "deep", "online", "agent"
    expert_panel_visible: bool = False
    profile_overrides: dict[str, Any] = field(default_factory=dict)

    # --- Execution State ---
    current_phase: MigrationPhase = MigrationPhase.MODE_SELECTION
    completed_phases: set[MigrationPhase] = field(default_factory=set)
    phase_completion_order: list[MigrationPhase] = field(default_factory=list)

    # --- Runtime Data (Results from Service Execution) ---
    # Hardware and Software Inventory
    hardware_inventory: dict[str, Any] | None = None
    software_inventory: dict[str, Any] | None = None

    # Analysis Results
    hardware_analysis: dict[str, Any] | None = None
    software_analysis: dict[str, Any] | None = None

    # Recommendations
    app_recommendations: dict[str, Any] | None = None
    file_recommendations: dict[str, Any] | None = None

    # Backup Results
    backup_manifest: dict[str, Any] | None = None
    backup_location: str | None = None

    # Restore Results
    restore_result: dict[str, Any] | None = None
    validation_result: dict[str, Any] | None = None

    # Final Report
    final_report: dict[str, Any] | None = None

    # --- Quality Metrics ---
    total_sovereignty_score: int = 0
    restored_data_size_label: str = ""

    # --- Activity Logging ---
    activity_entries: list[ActivityEntry] = field(default_factory=list)
    activity_filters: dict[str, bool] = field(
        default_factory=lambda: {
            "info": True,
            "done": True,
            "warn": True,
            "fail": True,
        }
    )

    # --- Error Tracking ---
    last_error: str | None = None
    last_error_details: dict[str, Any] | None = None

    # --- Auto-Execution State ---
    auto_running: bool = False
    total_actions: int = 0
    completed_actions: set[str] = field(default_factory=set)

    # --- Timestamps ---
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)

    # --- Temporary Working State ---
    working_data: dict[str, Any] = field(default_factory=dict)

    # =========================================================================
    # STATE QUERY METHODS
    # =========================================================================

    def get_completion_percentage(self) -> float:
        """Calculate migration completion percentage."""
        if self.total_actions == 0:
            return 0.0
        return (len(self.completed_actions) / self.total_actions) * 100.0

    def is_phase_complete(self, phase: MigrationPhase) -> bool:
        """Check if a specific phase has been completed."""
        return phase in self.completed_phases

    def is_phase_current(self, phase: MigrationPhase) -> bool:
        """Check if a specific phase is the current one."""
        return self.current_phase == phase

    def get_filtered_activities(self) -> list[ActivityEntry]:
        """Return activity entries filtered by active filters."""
        return [
            entry for entry in self.activity_entries
            if self.activity_filters.get(entry.level.value, True)
        ]

    def has_error(self) -> bool:
        """Check if there's a current error state."""
        return self.last_error is not None

    # =========================================================================
    # STATE MODIFICATION METHODS
    # =========================================================================

    def mark_phase_started(self, phase: MigrationPhase) -> None:
        """Record the start of a phase."""
        self.current_phase = phase
        self.last_modified = datetime.utcnow()
        self.log_activity(
            level=ActivityLevel.INFO,
            phase=phase,
            message=f"Phase started: {phase.value}",
        )

    def mark_phase_complete(self, phase: MigrationPhase) -> None:
        """Record completion of a phase."""
        self.completed_phases.add(phase)
        self.phase_completion_order.append(phase)
        self.last_modified = datetime.utcnow()
        self.log_activity(
            level=ActivityLevel.SUCCESS,
            phase=phase,
            message=f"Phase completed: {phase.value}",
        )

    def mark_action_complete(self, action_name: str) -> None:
        """Record completion of a named action."""
        self.completed_actions.add(action_name)
        self.last_modified = datetime.utcnow()

    def record_error(self, error_message: str, details: dict[str, Any] | None = None) -> None:
        """Record an error event."""
        self.last_error = error_message
        self.last_error_details = details or {}
        self.last_modified = datetime.utcnow()
        self.log_activity(
            level=ActivityLevel.ERROR,
            phase=self.current_phase,
            message=error_message,
            details=details or {},
        )

    def clear_error(self) -> None:
        """Clear the current error state."""
        self.last_error = None
        self.last_error_details = None
        self.last_modified = datetime.utcnow()

    def log_activity(
        self,
        level: ActivityLevel,
        phase: MigrationPhase | None,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add an activity entry to the log."""
        entry = ActivityEntry(
            timestamp=datetime.utcnow(),
            level=level,
            phase=phase,
            message=message,
            details=details or {},
        )
        self.activity_entries.append(entry)
        self.last_modified = datetime.utcnow()

    def set_toggle_filter(self, level_name: str, enabled: bool) -> None:
        """Toggle activity filter visibility."""
        if level_name in self.activity_filters:
            self.activity_filters[level_name] = enabled
            self.last_modified = datetime.utcnow()

    def store_result(self, key: str, data: Any) -> None:
        """Store execution result for a named key."""
        if key == "hardware_inventory":
            self.hardware_inventory = data
        elif key == "software_inventory":
            self.software_inventory = data
        elif key == "hardware_analysis":
            self.hardware_analysis = data
        elif key == "software_analysis":
            self.software_analysis = data
        elif key == "app_recommendations":
            self.app_recommendations = data
        elif key == "file_recommendations":
            self.file_recommendations = data
        elif key == "backup_manifest":
            self.backup_manifest = data
        elif key == "backup_location":
            self.backup_location = data
        elif key == "restore_result":
            self.restore_result = data
        elif key == "validation_result":
            self.validation_result = data
        elif key == "final_report":
            self.final_report = data
        else:
            # Store in working_data for transient values
            self.working_data[key] = data
        self.last_modified = datetime.utcnow()

    def get_result(self, key: str) -> Any:
        """Retrieve a stored result by key."""
        if key == "hardware_inventory":
            return self.hardware_inventory
        elif key == "software_inventory":
            return self.software_inventory
        elif key == "hardware_analysis":
            return self.hardware_analysis
        elif key == "software_analysis":
            return self.software_analysis
        elif key == "app_recommendations":
            return self.app_recommendations
        elif key == "file_recommendations":
            return self.file_recommendations
        elif key == "backup_manifest":
            return self.backup_manifest
        elif key == "backup_location":
            return self.backup_location
        elif key == "restore_result":
            return self.restore_result
        elif key == "validation_result":
            return self.validation_result
        elif key == "final_report":
            return self.final_report
        else:
            return self.working_data.get(key)

    def reset_for_new_session(self) -> None:
        """Reset state for a new migration session while preserving configuration."""
        self.current_phase = MigrationPhase.MODE_SELECTION
        self.completed_phases.clear()
        self.phase_completion_order.clear()
        self.activity_entries.clear()
        self.completed_actions.clear()
        self.last_error = None
        self.last_error_details = None

        # Clear execution results
        self.hardware_inventory = None
        self.software_inventory = None
        self.hardware_analysis = None
        self.software_analysis = None
        self.app_recommendations = None
        self.file_recommendations = None
        self.backup_manifest = None
        self.backup_location = None
        self.restore_result = None
        self.validation_result = None
        self.final_report = None
        self.working_data.clear()

        self.last_modified = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary for persistence/logging."""
        return {
            "runtime_mode": self.runtime_mode,
            "migration_mode": self.migration_mode,
            "target_distro": self.target_distro,
            "current_phase": self.current_phase.value,
            "completed_phases": [p.value for p in self.completed_phases],
            "completion_percentage": self.get_completion_percentage(),
            "has_error": self.has_error(),
            "last_error": self.last_error,
            "total_actions": self.total_actions,
            "completed_actions_count": len(self.completed_actions),
            "activity_count": len(self.activity_entries),
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
        }
