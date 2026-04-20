"""Inventory service modules for hardware and software collection."""

from __future__ import annotations

from src.services.inventory.hardware import HardwareInventoryService
from src.services.inventory.software import SoftwareInventoryService

__all__ = [
    "HardwareInventoryService",
    "SoftwareInventoryService",
]
