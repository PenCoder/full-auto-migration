"""
Software mapping analysis module for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

Responsibilities:
1. Load configuration and locate software_inventory.json.
2. Load raw software inventory as produced by src/inventory/software.py.
3. Filter out non-user-facing components (SDKs, runtimes, redistributables, frameworks).
4. Classify remaining entries as relevant applications.
5. Suggest Linux Mint equivalents for common applications.
6. Write a structured CSV mapping table (software_mapping.csv) for further analysis.

This module operates on previously collected data and does not access
the Windows registry directly.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from src.constants import BASE_DIR, DATA_DIR, RESTORE_DIR
from src.loggers import get_logger
from src.config import load_default_config, load_config, MigrationConfigRoot, load_software_mapping
from src.analysis.dynamic_rules import resolve_mapping
from src.services.profile_service import ProfileService


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = get_logger("analysis.software_mapping")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_str(value: Any) -> str:
    """
    Convert any value to a normalized string (or empty string if None).
    """
    if value is None:
        return ""
    return str(value).strip()


def _load_software_inventory(inventory_path: Path) -> List[Dict[str, Any]]:
    """
    Load software_inventory.json and return the list of entries.

    Parameters
    ----------
    inventory_path : Path
        Path to the software inventory JSON file.

    Returns
    -------
    List[Dict[str, Any]]
        List of software entries.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the JSON structure is invalid or missing 'entries'.
    """
    if not inventory_path.exists():
        raise FileNotFoundError(f"Software inventory file not found: {inventory_path}")

    with inventory_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Software inventory must be a JSON object at the top level.")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Software inventory JSON must contain a list under 'entries'.")

    return entries


# ---------------------------------------------------------------------------
# Filtering and classification
# ---------------------------------------------------------------------------

# Substrings that typically indicate system/framework components
EXCLUDE_SUBSTRINGS = [
    "redistributable",
    "runtime",
    "sdk",
    "targeting pack",
    "workload",
    "framework",
    "driver",
    "extension",
    "toolchain",
    "language pack",
    "update for",
    "intellisense",
    "diagnosticshub",
    "app certification kit",
    "xevent",
    "batch parser",
]

# Known user-facing applications that must not be filtered out even if
# their names contain technical words.
WHITELIST_NAMES = [
    "Microsoft Office",
    "Microsoft 365",
    "Microsoft Teams",
    "Microsoft Outlook",
    "Visual Studio",
    "Visual Studio Code",
    "Google Chrome",
    "Mozilla Firefox",
    "VLC media player",
    "GIMP",
    "Thunderbird",
]

def is_relevant_application(display_name: str, publisher: str) -> bool:
    """
    Determine whether a software entry should be considered for
    the mapping table.

    Parameters
    ----------
    display_name : str
        DisplayName from the inventory.
    publisher : str
        Publisher from the inventory.

    Returns
    -------
    bool
        True if the application is considered relevant (user-facing),
        False if it appears to be a framework, runtime, SDK, etc.
    """
    name_l = display_name.lower()
    if name_l.startswith("vs_") or name_l.startswith("wptx") or "application verifier" in name_l:
        return False
    if "sql server 2022" in name_l and any(k in name_l for k in ["batch parser", "xevent", "shared", "common files", "connection info", "sql diagnostics", "shared management objects"]):
        return False
    
    pub_l = publisher.lower()

    if not display_name:
        return False

    # Whitelist has priority
    for w in WHITELIST_NAMES:
        if w.lower() in name_l:
            return True

    # Exclude obvious system/framework components
    for ex in EXCLUDE_SUBSTRINGS:
        if ex in name_l:
            return False
        
    # Exclude Microsoft .NET and Visual C++ runtimes
    if "microsoft" in pub_l and any(ex in name_l for ex in [".net", "visual c++", "vc++"]):
        return False

    # Otherwise, treat it as relevant. Manual refinement can be done later.
    return True


def classify_category(display_name: str, publisher: str) -> str:
    """
    Assign a coarse category to a relevant application.

    Parameters
    ----------
    display_name : str
        Application name.
    publisher : str
        Publisher string.

    Returns
    -------
    str
        Category label (e.g., 'Browser', 'Office', 'Media', 'Development', etc.).
    """
    name_l = display_name.lower()
    pub_l = publisher.lower()

    if any(k in name_l for k in ["chrome", "firefox", "edge", "brave", "opera"]):
        return "Browser"

    if any(k in name_l for k in ["office", "word", "excel", "powerpoint", "libreoffice"]):
        return "Office"

    if "outlook" in name_l or "thunderbird" in name_l or "mail" in name_l:
        return "Mail"

    if any(k in name_l for k in ["vlc", "media player", "spotify", "itunes", "music", "video"]):
        return "Media"

    if any(k in name_l for k in ["visual studio", "jetbrains", "pycharm", "intellij", "eclipse", "android studio", "code"]):
        return "Development"

    if any(k in name_l for k in ["zoom", "teams", "slack", "skype", "discord"]):
        return "Communication"

    if any(k in name_l for k in ["pdf", "backup", "sync", "antivirus", "security"]):
        return "Utility"

    return "Other"


# Mapping from known Windows applications to suggested Linux/Linux Mint equivalents.
KNOWN_MAPPINGS = {
    "microsoft office": ("LibreOffice", "Install Linux equivalent"),
    "microsoft 365": ("LibreOffice + browser-based Office", "Use web version and local equivalent"),
    "google chrome": ("Google Chrome for Linux", "Install Linux equivalent"),
    "mozilla firefox": ("Firefox (preinstalled on Mint)", "Use preinstalled browser"),
    "vlc media player": ("VLC (Linux)", "Install Linux equivalent (often available in repo)"),
    "gimp": ("GIMP (Linux)", "Install Linux equivalent"),
    "microsoft teams": ("Microsoft Teams (Linux/web)", "Prefer web or Linux client if supported"),
    "microsoft outlook": ("Thunderbird", "Install Linux equivalent mail client"),
    "visual studio code": ("VS Code (Linux)", "Install Linux equivalent"),
    "thunderbird": ("Thunderbird (Linux)", "Install Linux equivalent"),
}


# ---------------------------------------------------------------------------
# Matrix generation
# ---------------------------------------------------------------------------

def generate_software_mapping(
    config: MigrationConfigRoot,
    entries: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Generate a software mapping table from raw inventory entries.

    Parameters
    ----------
    config : MigrationConfigRoot
        Loaded configuration (currently unused; kept for extensibility).
    entries : List[Dict[str, Any]]
        Raw software inventory entries.

    Returns
    -------
    List[Dict[str, str]]
        List of rows for the software mapping table with fields:
        windows_name, publisher, category, linux_package, migration_strategy, notes.
    """
    rows: List[Dict[str, str]] = []

    mapping = load_software_mapping(config.migration.software_map_config)
    profile_path = Path(config.automation.active_profile_path)
    if not profile_path.is_absolute():
        profile_path = BASE_DIR / profile_path
    overrides = ProfileService(profile_path=profile_path).get_mapping_overrides()
    
    for entry in entries:
        display_name = _normalize_str(entry.get("DisplayName"))
        publisher = _normalize_str(entry.get("Publisher"))

        if not is_relevant_application(display_name, publisher):
            continue

        category = classify_category(display_name, publisher)

        decision = resolve_mapping(
            display_name=display_name,
            base_mappings=mapping,
            overrides=overrides,
        )
        if not decision:
            continue

        rows.append({
            "windows_name": display_name,
            "publisher": publisher,
            "category": category,
            "linux_package": decision.linux_package,
            "linux_display_name": decision.linux_display_name,
            "migration_strategy": decision.migration_strategy,
            "notes": decision.notes,
            "confidence_score": f"{decision.confidence_score:.2f}",
            "recommendation_source": decision.recommendation_source,
        })

    return rows


def write_software_mapping(
    rows: List[Dict[str, str]],
    filename: str = "software_mapping.csv",
    apps_to_install: Optional[str] = "apps_to_install.json",
) -> Path:
    """
    Write software mapping table to CSV under ./data/analysis.

    Parameters
    ----------
    rows : List[Dict[str, str]]
        Rows as produced by generate_software_mapping().
    filename : str, optional
        Output CSV file name, by default "software_mapping.csv".

    Returns
    -------
    Path
        Full path to the written CSV file.
    """
    analysis_dir = DATA_DIR / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    out_path = analysis_dir / filename
    restore_apps_path = RESTORE_DIR / apps_to_install
    logger.info("Writing software mapping table to: %s", out_path)

    fieldnames = [
        "windows_name",
        "publisher",
        "category",
        "linux_package",
        "migration_strategy",
        "linux_display_name",
        "notes",
        "confidence_score",
        "recommendation_source",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # Additionally, write a JSON file with applications to install
    apps_list = [
        {   
            "windows_name": row["windows_name"],
            "display_name": row["linux_display_name"],
            "linux_package": row["linux_package"],
            "migration_strategy": row["migration_strategy"],
        }
        for row in rows
        if row["migration_strategy"].lower() in ("apt", "manual install", "install linux equivalent")
    ]
    restore_apps_path.parent.mkdir(parents=True, exist_ok=True)
    with restore_apps_path.open("w", encoding="utf-8") as f:
        json.dump({"applications": apps_list}, f, indent=2)
    logger.info("Applications to install written to: %s", restore_apps_path)

    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(config_path: Optional[str] = None, inventory_filename: str = "software_inventory.json") -> None:
    """
    Command-line entry point for generating the software mapping table.

    Steps:
    1. Setup logging.
    2. Load configuration.
    3. Load software inventory JSON from inventory_output_dir.
    4. Filter and classify relevant applications.
    5. Write software_mapping.csv to ./data/analysis.
    """

    if config_path is None:
        logger.info("Loading default configuration...")
        cfg = load_default_config()
    else:
        logger.info("Loading configuration from: %s", config_path)
        cfg = load_config(config_path)
    
    inv_dir = DATA_DIR / cfg.source_system.inventory_output_dir
    inventory_path = inv_dir / inventory_filename

    logger.info("Loading software inventory from: %s", inventory_path)
    entries = _load_software_inventory(inventory_path)

    rows = generate_software_mapping(cfg, entries)
    out_file = write_software_mapping(rows)

    logger.info("Software mapping table written to: %s", out_file)


if __name__ == "__main__":
    main()
