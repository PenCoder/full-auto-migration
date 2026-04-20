"""Software analysis service implementation."""

from __future__ import annotations

from typing import Any
from src.loggers import get_logger
from src.analysis.software_mapping import generate_software_mapping, write_software_mapping


class SoftwareAnalysisService:
    """Specialized service for software compatibility mapping.
    
    Responsibilities:
    - Analyze software inventory for Linux alternatives
    - Generate software mapping recommendations
    - Persist analysis results
    - Handle software-specific analysis errors
    """

    def __init__(self, config: Any):
        """Initialize software analysis service.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.analysis.software")

    def analyze(self, sw_inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze software inventory for Linux alternatives.
        
        Args:
            sw_inventory: Software inventory data from SoftwareInventoryService
            
        Returns:
            Dictionary containing software mapping analysis
            
        Raises:
            Exception: If analysis fails
        """
        self.logger.info("Starting software mapping analysis...")
        try:
            entries = sw_inventory.get("entries", [])
            analysis = generate_software_mapping(self.config, entries)
            self.logger.info("Software mapping analysis completed")
            return analysis
        except Exception as exc:
            self.logger.exception("Software analysis failed: %s", exc)
            raise

    def persist(self, analysis: dict[str, Any]) -> str:
        """Persist software analysis to output file.
        
        Args:
            analysis: Analysis data to persist
            
        Returns:
            Path to the written file
            
        Raises:
            Exception: If persistence fails
        """
        self.logger.info("Persisting software analysis to file...")
        try:
            output_path = write_software_mapping(analysis)
            self.logger.info("Software analysis persisted to %s", output_path)
            return str(output_path)
        except Exception as exc:
            self.logger.exception("Failed to persist software analysis: %s", exc)
            raise

    def analyze_and_persist(self, sw_inventory: dict[str, Any]) -> dict[str, Any]:
        """Analyze software and immediately persist results.
        
        Args:
            sw_inventory: Software inventory data
            
        Returns:
            Dictionary with keys:
            - 'data': Analysis data
            - 'file_path': Path to persisted file
        """
        analysis = self.analyze(sw_inventory)
        file_path = self.persist(analysis)
        return {"data": analysis, "file_path": file_path}
