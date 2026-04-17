"""
Hardware inventory module for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

This module is responsible for:
1. Loading the project configuration.
2. Determining the correct output directory for inventory data.
3. Executing PowerShell commands on Windows to collect hardware information.
4. Parsing the returned JSON data into Python structures.
5. Assembling a structured hardware inventory document.
6. Writing the result to a JSON file (hardware_inventory.json).
7. Providing a CLI entry point for standalone execution.

The module is intentionally conservative:
- It uses only standard Windows PowerShell cmdlets.
- It handles missing features (e.g. TPM, Secure Boot on BIOS) gracefully.
- It fails with clear error messages if something critical goes wrong.

This module MUST be executed on a Windows system with PowerShell available.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.constants import BASE_DIR, DATA_DIR
from src.loggers import get_logger
from src.config import load_default_config, MigrationConfigRoot

# ---------------------------------------------------------------------------
# PowerShell helpers
# ---------------------------------------------------------------------------

logger = get_logger("inventory.hardware")

def _run_powershell_json(command: str) -> Any:
    """
    Execute a PowerShell command that produces JSON output and parse it.

    Parameters
    ----------
    command : str
        PowerShell command string which MUST end with a ConvertTo-Json call.

    Returns
    -------
    Any
        Parsed JSON object (dict, list, etc.), or None if no data is returned.

    Raises
    ------
    RuntimeError
        If the PowerShell process fails or returns invalid JSON.
    """
    full_command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]

    logger.debug("Executing PowerShell command: %s", command)

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "PowerShell executable not found. This module must be run on "
            "Windows with PowerShell available in PATH."
        ) from e

    if result.returncode != 0:
        logger.error("PowerShell error: %s", result.stderr.strip())
        raise RuntimeError(
            f"PowerShell command failed with exit code {result.returncode}"
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        logger.debug("PowerShell returned no output.")
        return None

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse PowerShell JSON output: %s", stdout)
        raise RuntimeError("Invalid JSON returned from PowerShell.") from e

    return data


# ---------------------------------------------------------------------------
# Hardware collection functions
# ---------------------------------------------------------------------------

def _collect_cpu_info() -> Any:
    """
    Collect CPU information using Win32_Processor.

    Returns
    -------
    Any
        JSON-decoded representation of the selected CPU fields.
    """
    cmd = (
        "Get-CimInstance Win32_Processor | "
        "Select-Object Name,Manufacturer,NumberOfCores,"
        "NumberOfLogicalProcessors,MaxClockSpeed,ProcessorId | "
        "ConvertTo-Json -Depth 4"
    )
    return _run_powershell_json(cmd)


def _collect_memory_info() -> Any:
    """
    Collect physical memory (RAM) information using Win32_PhysicalMemory.
    """
    cmd = (
        "Get-CimInstance Win32_PhysicalMemory | "
        "Select-Object Manufacturer,PartNumber,Capacity,Speed,SerialNumber | "
        "ConvertTo-Json -Depth 4"
    )
    return _run_powershell_json(cmd)


def _collect_gpu_info() -> Any:
    """
    Collect GPU (video controller) information using Win32_VideoController.
    """
    cmd = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterCompatibility,DriverVersion,DriverDate,"
        "VideoProcessor,AdapterRAM | "
        "ConvertTo-Json -Depth 4"
    )
    return _run_powershell_json(cmd)


def _collect_disk_info() -> Any:
    """
    Collect physical disk information using Win32_DiskDrive.
    """
    cmd = (
        "Get-CimInstance Win32_DiskDrive | "
        "Select-Object Index,Model,Manufacturer,SerialNumber,InterfaceType,"
        "MediaType,Size | "
        "ConvertTo-Json -Depth 4"
    )
    return _run_powershell_json(cmd)


def _collect_logical_disk_info() -> Any:
    """
    Collect logical disk / partition information using Win32_LogicalDisk.
    """
    cmd = (
        "Get-CimInstance Win32_LogicalDisk | "
        "Select-Object DeviceID,VolumeName,FileSystem,Size,FreeSpace,DriveType | "
        "ConvertTo-Json -Depth 4"
    )
    return _run_powershell_json(cmd)


def _collect_network_adapter_info() -> Any:
    """
    Collect physical network adapter information using Win32_NetworkAdapter.

    Only physical adapters are selected (PhysicalAdapter = true).
    """
    cmd = (
        "Get-CimInstance Win32_NetworkAdapter | "
        "Where-Object {$_.PhysicalAdapter -eq $true} | "
        "Select-Object Name,Manufacturer,MACAddress,NetEnabled,AdapterType,PNPDeviceID | "
        "ConvertTo-Json -Depth 4"
    )
    return _run_powershell_json(cmd)


def _collect_os_firmware_info() -> Dict[str, Any]:
    """
    Collect OS, BIOS, and firmware-related information.

    Includes:
    - OS details (caption, version, build)
    - Computer system model
    - BIOS version and serial
    - Firmware type (BIOS vs UEFI, if detectable)
    - Secure Boot status (if available)
    - TPM presence and readiness (if available)
    """

    # OS info
    os_cmd = (
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption,Version,BuildNumber,InstallDate,LastBootUpTime | "
        "ConvertTo-Json -Depth 4"
    )
    os_info = _run_powershell_json(os_cmd)

    # Computer system
    cs_cmd = (
        "Get-CimInstance Win32_ComputerSystem | "
        "Select-Object Manufacturer,Model | "
        "ConvertTo-Json -Depth 4"
    )
    cs_info = _run_powershell_json(cs_cmd)

    # BIOS info
    bios_cmd = (
        "Get-CimInstance Win32_BIOS | "
        "Select-Object SerialNumber,BIOSVersion,ReleaseDate | "
        "ConvertTo-Json -Depth 4"
    )
    bios_info = _run_powershell_json(bios_cmd)

    # Firmware type: registry PEFirmwareType (if available).
    fw_cmd = r"""
    $value = -1
    try {
        $value = Get-ItemPropertyValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Control' -Name 'PEFirmwareType' -ErrorAction Stop
    } catch {
        $value = -1
    }
    $value | ConvertTo-Json -Depth 4
    """

    firmware_type = "Unknown"
    try:
        fw_val = _run_powershell_json(fw_cmd)
        if fw_val == 1:
            firmware_type = "BIOS"
        elif fw_val == 2:
            firmware_type = "UEFI"
        else:
            firmware_type = "Unknown"
    except RuntimeError:
        firmware_type = "Unknown"

    # Secure Boot (may fail on BIOS systems → keep None)
    secure_boot_enabled: Optional[bool] = None
    sb_cmd = "Confirm-SecureBootUEFI | ConvertTo-Json -Depth 4"
    try:
        secure_boot_enabled = bool(_run_powershell_json(sb_cmd))
    except RuntimeError:
        secure_boot_enabled = None

    # TPM information (may not exist)
    tpm_cmd = (
        "Get-Tpm | "
        "Select-Object TpmPresent,TpmReady,SpecVersion | "
        "ConvertTo-Json -Depth 4"
    )
    tpm_info: Optional[Dict[str, Any]] = None
    try:
        tpm_raw = _run_powershell_json(tpm_cmd)
        if isinstance(tpm_raw, dict):
            tpm_info = {
                "TpmPresent": tpm_raw.get("TpmPresent"),
                "TpmReady": tpm_raw.get("TpmReady"),
                "SpecVersion": tpm_raw.get("SpecVersion"),
            }
    except RuntimeError:
        tpm_info = None

    return {
        "os": os_info,
        "computer_system": cs_info,
        "bios": bios_info,
        "firmware_type": firmware_type,
        "secure_boot_enabled": secure_boot_enabled,
        "tpm": tpm_info,
    }


# ---------------------------------------------------------------------------
# Aggregation and output
# ---------------------------------------------------------------------------

def collect_hardware_inventory() -> Dict[str, Any]:
    """
    Collect hardware-related information from the current Windows system.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing structured hardware inventory.

    Raises
    ------
    RuntimeError
        If any critical PowerShell interaction fails.
    """
    logger.info("Collecting hardware inventory...")

    cpu = _collect_cpu_info()
    memory = _collect_memory_info()
    gpu = _collect_gpu_info()
    disks = _collect_disk_info()
    logical_disks = _collect_logical_disk_info()
    net_adapters = _collect_network_adapter_info()
    os_firmware = _collect_os_firmware_info()

    inventory: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "cpu": cpu,
        "memory": memory,
        "gpu": gpu,
        "disks": disks,
        "logical_disks": logical_disks,
        "network_adapters": net_adapters,
        "os_firmware": os_firmware,
    }

    logger.info("Hardware inventory collection completed.")
    return inventory


def write_hardware_inventory(
    config: MigrationConfigRoot,
    inventory: Dict[str, Any],
    filename: str = "hardware_inventory.json",
) -> Path:
    """
    Write the hardware inventory to the configured output directory.

    Parameters
    ----------
    config : MigrationConfigRoot
        Loaded configuration object, used to determine
        source_system.inventory_output_dir.
    inventory : Dict[str, Any]
        Hardware inventory dictionary returned from collect_hardware_inventory().
    filename : str, optional
        Output file name, by default "hardware_inventory.json".

    Returns
    -------
    Path
        Full path to the written inventory file.
    """
    out_dir = DATA_DIR / (config.source_system.inventory_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / filename
    
    logger.info("Writing hardware inventory to: %s", out_path)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)

    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(config_path: Optional[str] = None) -> None:
    """
    Command-line entry point for hardware inventory collection.

    This function:
    1. Sets up basic logging.
    2. Loads the configuration (either default or from the provided path).
    3. Collects the hardware inventory from the current Windows machine.
    4. Writes the inventory to the configured output directory.

    Parameters
    ----------
    config_path : Optional[str]
        Optional path to a custom configuration file. If None, the default
        config loader (configs/migration.config.yaml) is used.
    """

    if config_path is None:
        logger.info("Loading default configuration...")
        cfg = load_default_config()
    else:
        logger.info("Loading configuration from: %s", config_path)
        cfg = MigrationConfigRoot(**asdict(load_default_config()))  # Placeholder pattern if you later add a custom loader

    inv = collect_hardware_inventory()
    out_file = write_hardware_inventory(cfg, inv)
    logger.info("Hardware inventory written to: %s", out_file)


if __name__ == "__main__":
    # For simple standalone execution without argparse:
    main()
