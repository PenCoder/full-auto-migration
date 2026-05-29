"""Hardware inventory service implementation."""

from __future__ import annotations

from typing import Any
from src.loggers import get_logger
from src.inventory.hardware import collect_hardware_inventory, write_hardware_inventory


class HardwareInventoryService:
    """Specialized service for hardware inventory collection.
    
    Responsibilities:
    - Collect hardware information from the system
    - Persist hardware data to output files
    - Handle hardware-specific errors
    """

    def __init__(self, config: Any):
        """Initialize hardware inventory service.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.inventory.hardware")

    def collect(self) -> dict[str, Any]:
        """Collect hardware inventory from the system.
        
        Returns:
            Dictionary containing hardware information
            
        Raises:
            Exception: If hardware collection fails
        """
        self.logger.info("Starting hardware inventory collection...")
        try:
            hw_data = collect_hardware_inventory()
            self.logger.info("Hardware inventory collection completed successfully")
            return hw_data
        except Exception as exc:
            self.logger.exception("Hardware inventory collection failed: %s", exc)
            raise

    def persist(self, hw_data: dict[str, Any]) -> str:
        """Persist hardware inventory to output file.
        
        Args:
            hw_data: Hardware data to persist
            
        Returns:
            Path to the written file
            
        Raises:
            Exception: If persistence fails
        """
        self.logger.info("Persisting hardware inventory to file...")
        try:
            output_path = write_hardware_inventory(self.config, hw_data)
            self.logger.info("Hardware inventory persisted to %s", output_path)
            return str(output_path)
        except Exception as exc:
            self.logger.exception("Failed to persist hardware inventory: %s", exc)
            raise

    def collect_and_persist(self) -> dict[str, Any]:
        """Collect hardware inventory and immediately persist it.
        
        Returns:
            Dictionary with keys:
            - 'data': Hardware inventory data
            - 'file_path': Path to persisted file
        """
        hw_data = self.collect()
        file_path = self.persist(hw_data)
        return {"data": hw_data, "file_path": file_path}
