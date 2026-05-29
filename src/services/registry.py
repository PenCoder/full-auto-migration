"""Service registry and factory for dependency injection."""

from __future__ import annotations

from typing import Any

from src.core import WorkflowOrchestrator, MigrationState
from src.services.inventory import HardwareInventoryService, SoftwareInventoryService
from src.services.analysis import HardwareAnalysisService, SoftwareAnalysisService
from src.services.backup import BackupService
from src.services.recommendations import AppRecommendationService, FileRecommendationService
from src.services.report import ReportGenerationService
from src.services.restore import RestoreExecutionService
from src.loggers import get_logger


class ServiceRegistry:
    """Registry for managing service instances and their dependencies.
    
    Responsibilities:
    - Create service instances
    - Register services with orchestrator
    - Handle service configuration
    - Provide service lookup
    """

    def __init__(self, config: Any):
        """Initialize service registry.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.registry")
        self._services: dict[str, Any] = {}
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Create all service instances."""
        self.logger.info("Initializing services...")
        
        # Inventory services
        self._services["hardware_inventory"] = HardwareInventoryService(self.config)
        self._services["software_inventory"] = SoftwareInventoryService(self.config)
        
        # Analysis services
        self._services["hardware_analysis"] = HardwareAnalysisService(self.config)
        self._services["software_analysis"] = SoftwareAnalysisService(self.config)
        
        # Backup service
        self._services["backup"] = BackupService(self.config)
        
        # Recommendation services
        self._services["app_recommendations"] = AppRecommendationService(self.config)
        self._services["file_recommendations"] = FileRecommendationService(self.config)
        
        # Report service
        self._services["report"] = ReportGenerationService(self.config)
        
        self.logger.info("Services initialized successfully")

    def get_service(self, service_name: str) -> Any:
        """Retrieve a service by name.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service not found
        """
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' not registered")
        return self._services[service_name]

    def create_restore_service(self, bundle_dir: Any, target_home: Any) -> RestoreExecutionService:
        """Create a restore service instance.
        
        Args:
            bundle_dir: Directory containing backup bundle
            target_home: Target home directory
            
        Returns:
            RestoreExecutionService instance
        """
        return RestoreExecutionService(
            config=self.config,
            bundle_dir=bundle_dir,
            target_home=target_home,
        )

    def register_with_orchestrator(self, orchestrator: WorkflowOrchestrator) -> None:
        """Register all services with a workflow orchestrator.
        
        Args:
            orchestrator: WorkflowOrchestrator instance
        """
        self.logger.info("Registering services with orchestrator...")
        
        # Create wrapper objects that implement the protocols
        
        # Inventory service
        inventory_service = _InventoryServiceAdapter(
            hardware=self._services["hardware_inventory"],
            software=self._services["software_inventory"],
        )
        orchestrator.register_service("inventory", inventory_service)
        
        # Analysis service
        analysis_service = _AnalysisServiceAdapter(
            hardware=self._services["hardware_analysis"],
            software=self._services["software_analysis"],
        )
        orchestrator.register_service("analysis", analysis_service)
        
        # Backup service
        orchestrator.register_service("backup", self._services["backup"])
        
        # Recommendations service
        recommendations_service = _RecommendationsServiceAdapter(
            app=self._services["app_recommendations"],
            file=self._services["file_recommendations"],
        )
        orchestrator.register_service("recommendations", recommendations_service)
        
        # Report service
        orchestrator.register_service("report", self._services["report"])
        
        self.logger.info("Services registered with orchestrator")


# =============================================================================
# Service Adapters - Bridge pattern to implement protocols
# =============================================================================

class _InventoryServiceAdapter:
    """Adapter to implement InventoryService protocol."""

    def __init__(self, hardware: HardwareInventoryService, software: SoftwareInventoryService):
        self.hardware = hardware
        self.software = software
        self.logger = get_logger("adapters.inventory")

    def collect_hardware(self) -> dict[str, Any]:
        """Collect hardware inventory."""
        return self.hardware.collect()

    def collect_software(self, deep_scan: bool = False) -> dict[str, Any]:
        """Collect software inventory."""
        return self.software.collect(deep_scan=deep_scan)


class _AnalysisServiceAdapter:
    """Adapter to implement AnalysisService protocol."""

    def __init__(self, hardware: HardwareAnalysisService, software: SoftwareAnalysisService):
        self.hardware = hardware
        self.software = software
        self.logger = get_logger("adapters.analysis")

    def analyze_hardware(self, inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze hardware inventory."""
        return self.hardware.analyze(inventory)

    def analyze_software(self, inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze software inventory."""
        return self.software.analyze(inventory)


class _RecommendationsServiceAdapter:
    """Adapter to implement RecommendationService protocol."""

    def __init__(self, app: AppRecommendationService, file: FileRecommendationService):
        self.app = app
        self.file = file
        self.logger = get_logger("adapters.recommendations")

    def recommend_applications(
        self,
        software_inventory: dict[str, Any],
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate application recommendations."""
        return self.app.generate(software_inventory, selection_profile)

    def recommend_files(
        self,
        file_paths: list[str],
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate file recommendations."""
        return self.file.generate(file_paths, selection_profile)
