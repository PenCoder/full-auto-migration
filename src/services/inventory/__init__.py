"""Inventory service modules for hardware and software collection."""

from __future__ import annotations

from src.services.inventory.hardware import HardwareInventoryService
from src.services.inventory.software import SoftwareInventoryService

__all__ = [
    "HardwareInventoryService",
    "SoftwareInventoryService",
]


    def persist(self, sw_data: dict[str, Any]) -> str:
        """Persist software inventory to output file.
        
        Args:
            sw_data: Software data to persist
            
        Returns:
            Path to the written file
            
        Raises:
            Exception: If persistence fails
        """
        self.logger.info("Persisting software inventory to file...")
        try:
            output_path = write_software_inventory(self.config, sw_data)
            self.logger.info("Software inventory persisted to %s", output_path)
            return str(output_path)
        except Exception as exc:
            self.logger.exception("Failed to persist software inventory: %s", exc)
            raise

    def collect_and_persist(self, deep_scan: bool = False) -> dict[str, Any]:
        """Collect software inventory and immediately persist it.
        
        Args:
            deep_scan: Whether to perform deep scan
            
        Returns:
            Dictionary with keys:
            - 'data': Software inventory data
            - 'file_path': Path to persisted file
            - 'scan_type': Type of scan performed
        """
        sw_data = self.collect(deep_scan=deep_scan)
        file_path = self.persist(sw_data)
        return {
            "data": sw_data,
            "file_path": file_path,
            "scan_type": "deep" if deep_scan else "quick",
        }
