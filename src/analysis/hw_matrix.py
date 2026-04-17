"""
Hardware compatibility matrix generator for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

Responsibilities:
1. Load project configuration.
2. Locate and load hardware_inventory.json produced by src/inventory/hardware.py.
3. Extract relevant device information (GPU, network adapters, disks).
4. Classify devices according to expected Linux Mint support:
   - Native kernel support
   - Proprietary driver required
   - Potentially problematic / manual verification required
5. Write a structured CSV file (hardware_matrix.csv) to the analysis directory.
6. Provide a CLI entry point for standalone execution.

This module is read-only with respect to the source system: it does not
query hardware directly, but operates on previously collected inventory.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.constants import BASE_DIR, DATA_DIR
from src.loggers import get_logger
from src.config import load_default_config, load_config, MigrationConfigRoot


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logger = get_logger("analysis.hw_matrix")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _load_hardware_inventory(inventory_path: Path) -> Dict[str, Any]:
    """
    Load hardware_inventory.json from disk.

    Parameters
    ----------
    inventory_path : Path
        Path to the JSON inventory file.

    Returns
    -------
    Dict[str, Any]
        Parsed hardware inventory dictionary.

    Raises
    ------
    FileNotFoundError
        If the inventory file does not exist.
    ValueError
        If the file is not valid JSON or has an unexpected structure.
    """
    if not inventory_path.exists():
        raise FileNotFoundError(f"Hardware inventory file not found: {inventory_path}")

    with inventory_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Hardware inventory must be a JSON object at the top level.")

    return data


def _normalize_str(value: Any) -> str:
    """
    Convert any value to a normalized string (or empty string if None).

    Parameters
    ----------
    value : Any
        Input value.

    Returns
    -------
    str
        String representation with leading/trailing whitespace stripped.
    """
    if value is None:
        return ""
    return str(value).strip()


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

def classify_gpu(name: str, vendor: str) -> Dict[str, str]:
    """
    Classify GPU device in terms of Linux Mint support.

    Parameters
    ----------
    name : str
        GPU name (e.g., "NVIDIA GeForce GTX 1650").
    vendor : str
        AdapterCompatibility from Windows (e.g., "NVIDIA", "Intel Corporation").

    Returns
    -------
    Dict[str, str]
        Dictionary with classification fields: category, driver_strategy, notes.
    """
    name_l = name.lower()
    vendor_l = vendor.lower()

    if "nvidia" in name_l or "nvidia" in vendor_l:
        return {
            "category": "GPU",
            "driver_strategy": "Proprietary NVIDIA driver required",
            "notes": "Use nvidia-driver package recommended by Mint; test after install.",
        }

    if any(v in vendor_l for v in ["intel", "advanced micro devices", "amd"]) or \
       any(v in name_l for v in ["intel", "radeon", "vega", "rx ", "rtx ", "gtx "]):
        return {
            "category": "GPU",
            "driver_strategy": "Native kernel driver expected",
            "notes": "Intel/AMD typically supported by i915 or amdgpu; verify acceleration.",
        }

    return {
        "category": "GPU",
        "driver_strategy": "Unknown / manual check",
        "notes": "Unknown GPU vendor; check Mint hardware support resources.",
    }


def classify_network(name: str, vendor: str, pnp_id: str) -> Dict[str, str]:
    """
    Classify network adapter in terms of Linux Mint support.

    Parameters
    ----------
    name : str
        Adapter name.
    vendor : str
        Manufacturer.
    pnp_id : str
        PNPDeviceID (may contain PCI vendor/device IDs).

    Returns
    -------
    Dict[str, str]
        Classification dict.
    """
    name_l = name.lower()
    vendor_l = vendor.lower()
    pnp_l = pnp_id.lower()

    if "realtek" in vendor_l or "realtek" in name_l:
        return {
            "category": "Network",
            "driver_strategy": "Kernel driver + firmware (Realtek)",
            "notes": "Most Realtek NICs are supported, but some Wi-Fi chips require extra firmware.",
        }

    if "intel" in vendor_l or "intel" in name_l:
        return {
            "category": "Network",
            "driver_strategy": "Native Intel driver expected",
            "notes": "Intel wired/wireless NICs are generally well supported.",
        }

    if "broadcom" in vendor_l or "broadcom" in name_l:
        return {
            "category": "Network",
            "driver_strategy": "Broadcom-specific driver/firmware required",
            "notes": "Broadcom Wi-Fi often requires proprietary drivers (e.g., broadcom-sta); test post-install.",
        }

    # Simple heuristic: wireless vs wired from name
    if "wireless" in name_l or "wifi" in name_l or "wi-fi" in name_l:
        return {
            "category": "Network",
            "driver_strategy": "Wi-Fi adapter – manual verification",
            "notes": "Wi-Fi hardware requires verification; test connectivity in Live session.",
        }

    return {
        "category": "Network",
        "driver_strategy": "Generic/unknown network adapter",
        "notes": "Check with lspci/lsusb in Linux Mint and consult documentation if issues arise.",
    }


def classify_disk(model: str, interface_type: str, media_type: str) -> Dict[str, str]:
    """
    Classify disk device in terms of Linux Mint support.

    Parameters
    ----------
    model : str
        Model string.
    interface_type : str
        Interface type from Windows (e.g., "NVMe", "IDE", "SATA").
    media_type : str
        MediaType from Windows (if present).

    Returns
    -------
    Dict[str, str]
        Classification dict.
    """
    model_l = model.lower()
    interface_l = interface_type.lower()
    media_l = media_type.lower()

    if "nvme" in interface_l or "nvme" in model_l:
        return {
            "category": "Storage",
            "driver_strategy": "NVMe – native support in modern kernels",
            "notes": "Linux Mint supports NVMe; ensure correct disk selection during install.",
        }

    if "sata" in interface_l or "ssd" in model_l or "solid state" in media_l:
        return {
            "category": "Storage",
            "driver_strategy": "SATA/SSD – native support expected",
            "notes": "Standard SATA/SSD devices are supported by default.",
        }

    if "usb" in interface_l:
        return {
            "category": "Storage",
            "driver_strategy": "USB storage – supported",
            "notes": "External/USB drives are generally supported but not used for OS root.",
        }

    return {
        "category": "Storage",
        "driver_strategy": "Generic block device",
        "notes": "Disk type not clearly identified; verify visibility during Mint installation.",
    }


# ---------------------------------------------------------------------------
# Matrix generation
# ---------------------------------------------------------------------------

def generate_hardware_matrix(
    config: MigrationConfigRoot,
    inventory: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Generate a hardware compatibility matrix from the hardware inventory.

    Parameters
    ----------
    config : MigrationConfigRoot
        Loaded configuration object (currently unused, but included for future extensions).
    inventory : Dict[str, Any]
        Parsed hardware inventory.

    Returns
    -------
    List[Dict[str, str]]
        List of rows for the hardware matrix, each containing fields:
        device_type, name, vendor, identifier, driver_strategy, notes.
    """
    rows: List[Dict[str, str]] = []

    # GPUs
    gpu_entries = inventory.get("gpu") or []
    if isinstance(gpu_entries, dict):
        gpu_entries = [gpu_entries]

    for gpu in gpu_entries:
        name = _normalize_str(gpu.get("Name"))
        vendor = _normalize_str(gpu.get("AdapterCompatibility"))
        classification = classify_gpu(name, vendor)
        rows.append({
            "device_type": "GPU",
            "name": name,
            "vendor": vendor,
            "identifier": "",  # Could extend with PCI ID later if available
            "driver_strategy": classification["driver_strategy"],
            "notes": classification["notes"],
        })

    # Network adapters
    net_entries = inventory.get("network_adapters") or []
    if isinstance(net_entries, dict):
        net_entries = [net_entries]

    for net in net_entries:
        name = _normalize_str(net.get("Name"))
        vendor = _normalize_str(net.get("Manufacturer"))
        pnp_id = _normalize_str(net.get("PNPDeviceID"))
        classification = classify_network(name, vendor, pnp_id)
        rows.append({
            "device_type": "Network",
            "name": name,
            "vendor": vendor,
            "identifier": pnp_id,
            "driver_strategy": classification["driver_strategy"],
            "notes": classification["notes"],
        })

    # Disks
    disk_entries = inventory.get("disks") or []
    if isinstance(disk_entries, dict):
        disk_entries = [disk_entries]

    for disk in disk_entries:
        model = _normalize_str(disk.get("Model"))
        vendor = _normalize_str(disk.get("Manufacturer"))
        interface_type = _normalize_str(disk.get("InterfaceType"))
        media_type = _normalize_str(disk.get("MediaType"))
        classification = classify_disk(model, interface_type, media_type)
        rows.append({
            "device_type": "Storage",
            "name": model,
            "vendor": vendor,
            "identifier": interface_type,
            "driver_strategy": classification["driver_strategy"],
            "notes": classification["notes"],
        })

    return rows


def write_hardware_matrix(
    config: MigrationConfigRoot,
    rows: List[Dict[str, str]],
    filename: str = "hardware_matrix.csv",
) -> Path:
    """
    Write the hardware compatibility matrix to CSV.

    Parameters
    ----------
    config : MigrationConfigRoot
        Loaded configuration object.
    rows : List[Dict[str, str]]
        Matrix rows as produced by generate_hardware_matrix().
    filename : str, optional
        CSV file name, by default "hardware_matrix.csv".

    Returns
    -------
    Path
        Full path to the written CSV file.
    """
    # Store analysis outputs under ./data/analysis by convention
    analysis_dir = DATA_DIR / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    out_path = analysis_dir / filename
    logger.info("Writing hardware compatibility matrix to: %s", out_path)

    fieldnames = ["device_type", "name", "vendor", "identifier", "driver_strategy", "notes"]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(config_path: Optional[str] = None, inventory_filename: str = "hardware_inventory.json") -> None:
    """
    Command-line entry point for generating the hardware compatibility matrix.

    Steps:
    1. Set up logging.
    2. Load configuration.
    3. Load hardware inventory JSON from inventory_output_dir.
    4. Generate hardware matrix rows.
    5. Write hardware_matrix.csv to ./data/analysis.

    Parameters
    ----------
    config_path : Optional[str]
        Optional path to a custom configuration file. If None, the default
        config loader (configs/migration.config.yaml) is used.
    inventory_filename : str
        Name of the hardware inventory JSON file.
    """

    if config_path is None:
        logger.info("Loading default configuration...")
        cfg = load_default_config()
    else:
        logger.info("Loading configuration from: %s", config_path)
        cfg = load_config(config_path)

    inv_dir = DATA_DIR / cfg.source_system.inventory_output_dir
    inventory_path = inv_dir / inventory_filename

    logger.info("Loading hardware inventory from: %s", inventory_path)
    inventory = _load_hardware_inventory(inventory_path)

    rows = generate_hardware_matrix(cfg, inventory)
    out_file = write_hardware_matrix(cfg, rows)

    logger.info("Hardware compatibility matrix written to: %s", out_file)


if __name__ == "__main__":
    main()
