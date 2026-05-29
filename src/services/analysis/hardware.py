"""Hardware analysis service implementation."""

from __future__ import annotations

from typing import Any
from src.loggers import get_logger
from src.analysis.hw_matrix import generate_hardware_matrix, write_hardware_matrix


class HardwareAnalysisService:
    """Specialized service for hardware compatibility analysis.
    
    Responsibilities:
    - Analyze hardware inventory for Linux compatibility
    - Generate hardware compatibility matrix
    - Persist analysis results
    - Handle analysis-specific errors
    """

    def __init__(self, config: Any):
        """Initialize hardware analysis service.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.analysis.hardware")

    def analyze(self, hw_inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze hardware inventory for Linux compatibility.
        
        Args:
            hw_inventory: Hardware inventory data from HardwareInventoryService
            
        Returns:
            Dictionary containing hardware compatibility analysis
            
        Raises:
            Exception: If analysis fails
        """
        self.logger.info("Starting hardware compatibility analysis...")
        try:
            analysis = generate_hardware_matrix(self.config, hw_inventory)
            self.logger.info("Hardware compatibility analysis completed")
            return analysis
        except Exception as exc:
            self.logger.exception("Hardware analysis failed: %s", exc)
            raise

    def persist(self, analysis: dict[str, Any]) -> str:
        """Persist hardware analysis to output file.
        
        Args:
            analysis: Analysis data to persist
            
        Returns:
            Path to the written file
            
        Raises:
            Exception: If persistence fails
        """
        self.logger.info("Persisting hardware analysis to file...")
        try:
            output_path = write_hardware_matrix(self.config, analysis)
            self.logger.info("Hardware analysis persisted to %s", output_path)
            return str(output_path)
        except Exception as exc:
            self.logger.exception("Failed to persist hardware analysis: %s", exc)
            raise

    def analyze_and_persist(self, hw_inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze hardware and immediately persist results.
        
        Args:
            hw_inventory: Hardware inventory data
            
        Returns:
            Dictionary with keys:
            - 'data': Analysis data
            - 'file_path': Path to persisted file
        """
        analysis = self.analyze(hw_inventory)
        file_path = self.persist(analysis)
        return {"data": analysis, "file_path": file_path}
