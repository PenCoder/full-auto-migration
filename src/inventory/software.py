"""
Software inventory module for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

This module is responsible for:
1. Loading the project configuration.
2. Determining the correct output directory for inventory data.
3. Executing PowerShell commands on Windows to collect installed software
   information from standard registry locations.
4. Parsing the returned JSON data into Python structures.
5. Assembling a structured software inventory document.
6. Writing the result to a JSON file (software_inventory.json).
7. Providing a CLI entry point for standalone execution.

This module MUST be executed on a Windows system with PowerShell available.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import winapps as _winapps
except ImportError:
    _winapps = None  # type: ignore[assignment]

try:
    import winreg as _winreg
except ImportError:
    _winreg = None  # type: ignore[assignment]

from src.constants import BASE_DIR, DATA_DIR
from src.loggers import get_logger
from src.config import load_default_config, load_config, MigrationConfigRoot


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logger = get_logger("inventory.software")


# ---------------------------------------------------------------------------
# PowerShell helper
# ---------------------------------------------------------------------------

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
# Software inventory collection
# ---------------------------------------------------------------------------

_UNINSTALL_KEY_ROOTS: List[tuple] = []
if _winreg is not None:
    _UNINSTALL_KEY_ROOTS = [
        (_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]


def _collect_display_icons() -> Dict[str, str]:
    """Read DisplayIcon values from the uninstall registry keys, keyed by DisplayName.

    Used to find a representative icon (.exe or .ico path, possibly with a
    ",N" resource-index suffix) for each installed application.
    """
    if _winreg is None:
        return {}

    icons: Dict[str, str] = {}
    for hive, subkey in _UNINSTALL_KEY_ROOTS:
        try:
            root = _winreg.OpenKey(hive, subkey)
        except OSError:
            continue
        try:
            count = _winreg.QueryInfoKey(root)[0]
            for i in range(count):
                try:
                    name = _winreg.EnumKey(root, i)
                    with _winreg.OpenKey(root, name) as app_key:
                        display_name = _winreg.QueryValueEx(app_key, "DisplayName")[0]
                        try:
                            display_icon = _winreg.QueryValueEx(app_key, "DisplayIcon")[0]
                        except OSError:
                            display_icon = ""
                        if display_name and display_icon:
                            icons[display_name] = display_icon
                except OSError:
                    continue
        finally:
            root.Close()
    return icons


def _collect_software_from_registry() -> List[Dict[str, Any]]:
    """Return installed Windows applications via winapps, or an empty list on non-Windows."""
    if _winapps is None:
        logger.warning("winapps is not available on this platform — returning empty software list.")
        return []

    icons = _collect_display_icons()

    data: list[dict[str, Any]] = []
    for app in _winapps.list_installed():
        data.append({
            "DisplayName": app.name,
            "DisplayVersion": app.version,
            "Publisher": app.publisher,
            "InstallDate": None,
            "DisplayIcon": icons.get(app.name, ""),
        })
    return data


def _collect_packages_from_package_manager() -> List[Dict[str, Any]]:
    ps_script = r"""
    try {
        Get-Package |
            Select-Object Name,Version,ProviderName,Source |
            ConvertTo-Json -Depth 4
    } catch {
        @() | ConvertTo-Json -Depth 4
    }
    """
    data = _run_powershell_json(ps_script)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def _collect_appx_packages() -> List[Dict[str, Any]]:
    ps_script = r"""
    try {
        Get-AppxPackage |
            Select-Object Name,Publisher,Version,InstallLocation |
            ConvertTo-Json -Depth 4
    } catch {
        @() | ConvertTo-Json -Depth 4
    }
    """
    data = _run_powershell_json(ps_script)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def _collect_startup_entries() -> List[Dict[str, Any]]:
    ps_script = r"""
    try {
        Get-CimInstance Win32_StartupCommand |
            Select-Object Name,Command,Location,User |
            ConvertTo-Json -Depth 4
    } catch {
        @() | ConvertTo-Json -Depth 4
    }
    """
    data = _run_powershell_json(ps_script)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def collect_software_inventory(deep_scan: bool = False) -> Dict[str, Any]:
    """
    Collect software inventory from the current Windows system.

    Returns
    -------
    Dict[str, Any]
        Dictionary with:
        - timestamp
        - entries: list of software entries
    """
    logger.info("Collecting software inventory...")

    entries = _collect_software_from_registry()

    inventory: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "entries": entries,
        "scan_depth": "deep" if deep_scan else "quick",
    }

    if deep_scan:
        pkg_entries = _collect_packages_from_package_manager()
        appx_entries = _collect_appx_packages()
        startup_entries = _collect_startup_entries()
        inventory["package_manager_entries"] = pkg_entries
        inventory["appx_entries"] = appx_entries
        inventory["startup_entries"] = startup_entries
        inventory["deep_scan_summary"] = {
            "registry_entries": len(entries),
            "package_manager_entries": len(pkg_entries),
            "appx_entries": len(appx_entries),
            "startup_entries": len(startup_entries),
        }

    logger.info("Software inventory collection completed. Total entries: %d", len(entries))
    return inventory


def write_software_inventory(
    config: MigrationConfigRoot,
    inventory: Dict[str, Any],
    filename: str = "software_inventory.json",
) -> Path:
    """
    Write the software inventory to the configured output directory.

    Parameters
    ----------
    config : MigrationConfigRoot
        Loaded configuration object, used to determine
        source_system.inventory_output_dir.
    inventory : Dict[str, Any]
        Software inventory dictionary returned from collect_software_inventory().
    filename : str, optional
        Output file name, by default "software_inventory.json".

    Returns
    -------
    Path
        Full path to the written inventory file.
    """
    out_dir = DATA_DIR / config.source_system.inventory_output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / filename

    logger.info("Writing software inventory to: %s", out_path)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)

    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(config_path: Optional[str] = None) -> None:
    """
    Command-line entry point for software inventory collection.

    This function:
    1. Sets up basic logging.
    2. Loads the configuration (either default or from the provided path).
    3. Collects the software inventory from the current Windows machine.
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
        cfg = load_config(config_path)

    inventory = collect_software_inventory()
    out_file = write_software_inventory(cfg, inventory)
    logger.info("Software inventory written to: %s", out_file)


if __name__ == "__main__":
    main()
