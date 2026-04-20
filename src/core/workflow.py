"""Workflow orchestration engine that coordinates service execution."""

from __future__ import annotations

from typing import Any, Callable, Optional
from datetime import datetime

from src.core.state import MigrationState, MigrationPhase, ActivityLevel
from src.core.interfaces import (
    InventoryService,
    AnalysisService,
    BackupService,
    RecommendationService,
    ReportService,
    RestoreService,
    TaskRunner,
    StateObserver,
)


class WorkflowOrchestrator:
    """Coordinates migration workflow execution with proper separation of concerns.
    
    Responsibilities:
    - State management (single source of truth)
    - Service orchestration (calling services in correct sequence)
    - Error handling and recovery
    - Progress tracking and reporting
    - Observer notification
    """

    def __init__(
        self,
        state: MigrationState,
        task_runner: TaskRunner | None = None,
    ):
        """Initialize the workflow orchestrator.
        
        Args:
            state: Centralized migration state object
            task_runner: Optional task runner for background execution
        """
        self.state = state
        self.task_runner = task_runner
        self._observers: list[StateObserver] = []
        self._service_registry: dict[str, Any] = {}

    # =========================================================================
    # Service Registration
    # =========================================================================

    def register_service(self, service_type: str, service: Any) -> None:
        """Register a service implementation.
        
        Args:
            service_type: Service identifier ("inventory", "analysis", "backup", etc.)
            service: Service implementation
        """
        self._service_registry[service_type] = service

    def get_service(self, service_type: str) -> Any:
        """Retrieve a registered service.
        
        Args:
            service_type: Service identifier
            
        Returns:
            Service implementation
            
        Raises:
            ValueError: If service not registered
        """
        if service_type not in self._service_registry:
            raise ValueError(f"Service '{service_type}' not registered")
        return self._service_registry[service_type]

    # =========================================================================
    # Observer Pattern
    # =========================================================================

    def attach_observer(self, observer: StateObserver) -> None:
        """Register a state observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach_observer(self, observer: StateObserver) -> None:
        """Unregister a state observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_phase_changed(self, new_phase: MigrationPhase, old_phase: MigrationPhase) -> None:
        """Notify all observers of phase change."""
        for observer in self._observers:
            try:
                observer.on_phase_changed(new_phase.value, old_phase.value)
            except Exception as e:
                self.state.log_activity(
                    level=ActivityLevel.WARNING,
                    phase=new_phase,
                    message=f"Observer notification failed: {str(e)}",
                )

    def _notify_error(self, error_message: str, details: dict[str, Any]) -> None:
        """Notify all observers of error."""
        for observer in self._observers:
            try:
                observer.on_error_occurred(error_message, details)
            except Exception as e:
                self.state.log_activity(
                    level=ActivityLevel.WARNING,
                    phase=self.state.current_phase,
                    message=f"Observer error notification failed: {str(e)}",
                )

    def _notify_activity(self) -> None:
        """Notify all observers of recent activity."""
        for observer in self._observers:
            try:
                if self.state.activity_entries:
                    observer.on_activity_logged(self.state.activity_entries[-1])
            except Exception as e:
                pass  # Silently skip observer errors

    def _notify_progress(self) -> None:
        """Notify all observers of progress update."""
        percentage = self.state.get_completion_percentage()
        for observer in self._observers:
            try:
                observer.on_progress_updated(percentage)
            except Exception as e:
                pass  # Silently skip observer errors

    # =========================================================================
    # Workflow Execution
    # =========================================================================

    def execute_inventory_phase(
        self,
        deep_scan: bool = False,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        """Execute inventory collection phase.
        
        Args:
            deep_scan: Whether to perform deep scan
            on_complete: Callback on completion
            on_error: Callback on error
        """
        def _do_inventory():
            old_phase = self.state.current_phase
            self.state.mark_phase_started(MigrationPhase.INVENTORY)
            self._notify_phase_changed(MigrationPhase.INVENTORY, old_phase)

            try:
                inventory_svc = self.get_service("inventory")
                
                # Collect hardware inventory
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.INVENTORY,
                    message="Collecting hardware inventory...",
                )
                hw = inventory_svc.collect_hardware()
                self.state.store_result("hardware_inventory", hw)
                
                # Collect software inventory
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.INVENTORY,
                    message=f"Collecting software inventory (deep_scan={deep_scan})...",
                )
                sw = inventory_svc.collect_software(deep_scan=deep_scan)
                self.state.store_result("software_inventory", sw)
                
                self.state.mark_phase_complete(MigrationPhase.INVENTORY)
                self.state.mark_action_complete("inventory")
                self._notify_progress()
                
                if on_complete:
                    on_complete({"hardware": hw, "software": sw})
                
            except Exception as exc:
                self.state.record_error(
                    f"Inventory phase failed: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
                self._notify_error(f"Inventory phase failed: {str(exc)}", {"exception": str(exc)})
                if on_error:
                    on_error(f"Inventory phase failed", exc)

        self._execute_task(_do_inventory)

    def execute_analysis_phase(
        self,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        """Execute analysis phase.
        
        Args:
            on_complete: Callback on completion
            on_error: Callback on error
        """
        def _do_analysis():
            old_phase = self.state.current_phase
            self.state.mark_phase_started(MigrationPhase.ANALYSIS)
            self._notify_phase_changed(MigrationPhase.ANALYSIS, old_phase)

            try:
                # Get inventory results
                hw_inventory = self.state.get_result("hardware_inventory")
                sw_inventory = self.state.get_result("software_inventory")
                
                if not hw_inventory or not sw_inventory:
                    raise ValueError("Inventory must be completed before analysis")
                
                analysis_svc = self.get_service("analysis")
                
                # Analyze hardware
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.ANALYSIS,
                    message="Analyzing hardware compatibility...",
                )
                hw_analysis = analysis_svc.analyze_hardware(hw_inventory)
                self.state.store_result("hardware_analysis", hw_analysis)
                
                # Analyze software
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.ANALYSIS,
                    message="Analyzing software mappings...",
                )
                sw_analysis = analysis_svc.analyze_software(sw_inventory)
                self.state.store_result("software_analysis", sw_analysis)
                
                self.state.mark_phase_complete(MigrationPhase.ANALYSIS)
                self.state.mark_action_complete("analysis")
                self._notify_progress()
                
                if on_complete:
                    on_complete({"hardware": hw_analysis, "software": sw_analysis})
                
            except Exception as exc:
                self.state.record_error(
                    f"Analysis phase failed: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
                self._notify_error(f"Analysis phase failed: {str(exc)}", {"exception": str(exc)})
                if on_error:
                    on_error(f"Analysis phase failed", exc)

        self._execute_task(_do_analysis)

    def execute_recommendations_phase(
        self,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        """Execute recommendations phase.
        
        Args:
            on_complete: Callback on completion
            on_error: Callback on error
        """
        def _do_recommendations():
            old_phase = self.state.current_phase
            self.state.mark_phase_started(MigrationPhase.RECOMMENDATIONS)
            self._notify_phase_changed(MigrationPhase.RECOMMENDATIONS, old_phase)

            try:
                sw_inventory = self.state.get_result("software_inventory")
                if not sw_inventory:
                    raise ValueError("Software inventory required for recommendations")
                
                rec_svc = self.get_service("recommendations")
                
                # Generate app recommendations
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.RECOMMENDATIONS,
                    message="Generating application recommendations...",
                )
                app_recs = rec_svc.recommend_applications(
                    sw_inventory,
                    selection_profile=self.state.recommendation_strategy,
                )
                self.state.store_result("app_recommendations", app_recs)
                
                # Generate file recommendations
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.RECOMMENDATIONS,
                    message="Generating file recommendations...",
                )
                file_recs = rec_svc.recommend_files(
                    self.state.selected_folders.keys() if self.state.selected_folders else [],
                    selection_profile=self.state.recommendation_strategy,
                )
                self.state.store_result("file_recommendations", file_recs)
                
                self.state.mark_phase_complete(MigrationPhase.RECOMMENDATIONS)
                self.state.mark_action_complete("recommendations")
                self._notify_progress()
                
                if on_complete:
                    on_complete({"apps": app_recs, "files": file_recs})
                
            except Exception as exc:
                self.state.record_error(
                    f"Recommendations phase failed: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
                self._notify_error(f"Recommendations phase failed: {str(exc)}", {"exception": str(exc)})
                if on_error:
                    on_error(f"Recommendations phase failed", exc)

        self._execute_task(_do_recommendations)

    def execute_backup_phase(
        self,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        """Execute backup phase.
        
        Args:
            on_complete: Callback on completion
            on_error: Callback on error
        """
        def _do_backup():
            old_phase = self.state.current_phase
            self.state.mark_phase_started(MigrationPhase.BACKUP)
            self._notify_phase_changed(MigrationPhase.BACKUP, old_phase)

            try:
                backup_svc = self.get_service("backup")
                
                # Generate manifest
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.BACKUP,
                    message="Generating backup manifest...",
                )
                manifest = backup_svc.generate_manifest(
                    selected_folders=list(self.state.selected_folders.keys()),
                    selected_types=self.state.selected_file_types,
                )
                self.state.store_result("backup_manifest", manifest)
                
                # Create backup
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.BACKUP,
                    message="Creating backup bundle...",
                )
                backup_result = backup_svc.create_backup(
                    manifest=manifest,
                    output_dir=self.state.config.source_system.backup_output_dir,
                    compress=self.state.config.backup.compress,
                )
                self.state.store_result("backup_location", backup_result.get("location"))
                
                self.state.mark_phase_complete(MigrationPhase.BACKUP)
                self.state.mark_action_complete("backup")
                self._notify_progress()
                
                if on_complete:
                    on_complete(backup_result)
                
            except Exception as exc:
                self.state.record_error(
                    f"Backup phase failed: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
                self._notify_error(f"Backup phase failed: {str(exc)}", {"exception": str(exc)})
                if on_error:
                    on_error(f"Backup phase failed", exc)

        self._execute_task(_do_backup)

    def execute_restore_phase(
        self,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        """Execute restore phase.
        
        Args:
            on_complete: Callback on completion
            on_error: Callback on error
        """
        def _do_restore():
            old_phase = self.state.current_phase
            self.state.mark_phase_started(MigrationPhase.RESTORE)
            self._notify_phase_changed(MigrationPhase.RESTORE, old_phase)

            try:
                backup_location = self.state.get_result("backup_location")
                if not backup_location:
                    raise ValueError("Backup location not available")
                
                restore_svc = self.get_service("restore")
                
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.RESTORE,
                    message=f"Restoring from {backup_location}...",
                )
                restore_result = restore_svc.restore_backup(
                    backup_location=backup_location,
                    target_location=self.state.config.target_system.get("mount_point", "/mnt/target"),
                )
                self.state.store_result("restore_result", restore_result)
                
                self.state.mark_phase_complete(MigrationPhase.RESTORE)
                self.state.mark_action_complete("restore")
                self._notify_progress()
                
                if on_complete:
                    on_complete(restore_result)
                
            except Exception as exc:
                self.state.record_error(
                    f"Restore phase failed: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
                self._notify_error(f"Restore phase failed: {str(exc)}", {"exception": str(exc)})
                if on_error:
                    on_error(f"Restore phase failed", exc)

        self._execute_task(_do_restore)

    def execute_report_phase(
        self,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        """Execute report generation phase.
        
        Args:
            on_complete: Callback on completion
            on_error: Callback on error
        """
        def _do_report():
            old_phase = self.state.current_phase
            self.state.mark_phase_started(MigrationPhase.REPORT)
            self._notify_phase_changed(MigrationPhase.REPORT, old_phase)

            try:
                report_svc = self.get_service("report")
                
                self.state.log_activity(
                    level=ActivityLevel.INFO,
                    phase=MigrationPhase.REPORT,
                    message="Generating final report...",
                )
                report = report_svc.generate_report(
                    inventory={
                        "hardware": self.state.get_result("hardware_inventory"),
                        "software": self.state.get_result("software_inventory"),
                    },
                    analysis={
                        "hardware": self.state.get_result("hardware_analysis"),
                        "software": self.state.get_result("software_analysis"),
                    },
                    recommendations={
                        "apps": self.state.get_result("app_recommendations"),
                        "files": self.state.get_result("file_recommendations"),
                    },
                    validation=self.state.get_result("validation_result"),
                )
                self.state.store_result("final_report", report)
                
                self.state.mark_phase_complete(MigrationPhase.REPORT)
                self.state.mark_action_complete("report")
                self._notify_progress()
                
                if on_complete:
                    on_complete(report)
                
            except Exception as exc:
                self.state.record_error(
                    f"Report phase failed: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
                self._notify_error(f"Report phase failed: {str(exc)}", {"exception": str(exc)})
                if on_error:
                    on_error(f"Report phase failed", exc)

        self._execute_task(_do_report)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _execute_task(self, task_fn: Callable[[], None]) -> None:
        """Execute a task either asynchronously or synchronously.
        
        Args:
            task_fn: Task function to execute
        """
        if self.task_runner:
            self.task_runner.run_async(task_fn)
        else:
            task_fn()

    def get_workflow_status(self) -> dict[str, Any]:
        """Get current workflow status.
        
        Returns:
            Dictionary with workflow status information
        """
        return {
            "current_phase": self.state.current_phase.value,
            "completed_phases": [p.value for p in self.state.completed_phases],
            "completion_percentage": self.state.get_completion_percentage(),
            "has_error": self.state.has_error(),
            "last_error": self.state.last_error,
            "total_actions": self.state.total_actions,
            "completed_actions": len(self.state.completed_actions),
            "activity_count": len(self.state.activity_entries),
        }
