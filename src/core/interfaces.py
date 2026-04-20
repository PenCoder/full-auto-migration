"""Service interfaces and protocols defining the contract for all services."""

from __future__ import annotations

from typing import Any, Protocol, Callable


class InventoryService(Protocol):
    """Contract for hardware and software inventory collection services."""

    def collect_hardware(self) -> dict[str, Any]:
        """Collect hardware inventory from the system."""
        ...

    def collect_software(self, deep_scan: bool = False) -> dict[str, Any]:
        """Collect software inventory from the system."""
        ...


class AnalysisService(Protocol):
    """Contract for analysis services that process raw inventory data."""

    def analyze_hardware(self, inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze hardware inventory and produce compatibility matrix."""
        ...

    def analyze_software(self, inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze software inventory and produce mapping recommendations."""
        ...


class BackupService(Protocol):
    """Contract for backup creation and archival services."""

    def create_backup(
        self,
        manifest: dict[str, Any],
        output_dir: str,
        compress: bool = False,
    ) -> dict[str, Any]:
        """Create backup bundle from manifest specification."""
        ...

    def generate_manifest(
        self,
        selected_folders: list[str],
        selected_types: dict[str, bool],
    ) -> dict[str, Any]:
        """Generate backup manifest from selections."""
        ...


class RecommendationService(Protocol):
    """Contract for generating migration recommendations."""

    def recommend_applications(
        self,
        software_inventory: dict[str, Any],
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate Windows→Linux application recommendations."""
        ...

    def recommend_files(
        self,
        file_paths: list[str],
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate file migration recommendations."""
        ...


class ReportService(Protocol):
    """Contract for report generation services."""

    def generate_report(
        self,
        inventory: dict[str, Any],
        analysis: dict[str, Any],
        recommendations: dict[str, Any],
        validation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive migration report."""
        ...

    def format_report(
        self,
        report: dict[str, Any],
        format: str = "json",  # "json", "markdown", "html"
    ) -> str:
        """Format report in specified output format."""
        ...


class RestoreService(Protocol):
    """Contract for restore and validation services."""

    def restore_backup(
        self,
        backup_location: str,
        target_location: str,
    ) -> dict[str, Any]:
        """Execute restore of backup bundle to target location."""
        ...

    def validate_restore(
        self,
        backup_manifest: dict[str, Any],
        restored_location: str,
    ) -> dict[str, Any]:
        """Validate integrity and completeness of restored backup."""
        ...


# ============================================================================
# Callback Function Types
# ============================================================================

LogCallback = Callable[[str, str], None]
"""Callback type for logging (message, level)"""

ProgressCallback = Callable[[int, str], None]
"""Callback type for progress reporting (current, total)"""

CompletionCallback = Callable[[dict[str, Any]], None]
"""Callback type for task completion (result_data)"""

ErrorCallback = Callable[[str, Exception], None]
"""Callback type for error reporting (message, exception)"""


# ============================================================================
# Async Task Runner Protocol
# ============================================================================

class TaskRunner(Protocol):
    """Contract for background task execution."""

    def run_async(
        self,
        task_fn: Callable[[], Any],
        on_complete: CompletionCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        """Execute a task asynchronously with optional callbacks."""
        ...


# ============================================================================
# State Observer Protocol
# ============================================================================

class StateObserver(Protocol):
    """Contract for objects that observe state changes."""

    def on_phase_changed(self, new_phase: str, old_phase: str) -> None:
        """Called when migration phase changes."""
        ...

    def on_error_occurred(self, error_message: str, details: dict[str, Any]) -> None:
        """Called when an error occurs."""
        ...

    def on_activity_logged(self, activity_entry: Any) -> None:
        """Called when activity is logged."""
        ...

    def on_progress_updated(self, completion_percentage: float) -> None:
        """Called when completion progress updates."""
        ...
