"""Windows shortcut inventory — Desktop icons, Start Menu entries, and taskbar pins.

Captures the .lnk shortcuts a user actually sees and uses, then matches each
one to an installed application name so the Linux restore side can recreate
an equivalent launcher (.desktop entry) for whichever package replaced it.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import MigrationConfigRoot
from src.constants import DATA_DIR
from src.loggers import get_logger

try:
    import win32com.client as _win32com_client
except ImportError:
    _win32com_client = None  # type: ignore[assignment]

logger = get_logger("inventory.shortcuts")


def _normalize_name(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _shortcut_dirs() -> List[tuple]:
    """Return (category, directory, recursive) tuples to scan for .lnk files."""
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    programdata = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    public = Path(os.environ.get("PUBLIC", r"C:\Users\Public"))

    return [
        ("desktop", home / "Desktop", False),
        ("desktop", public / "Desktop", False),
        ("start_menu", appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs", True),
        ("start_menu", programdata / "Microsoft" / "Windows" / "Start Menu" / "Programs", True),
        ("taskbar", appdata / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar", False),
    ]


def _resolve_shortcut(shell, lnk_path: Path) -> Optional[Dict[str, str]]:
    try:
        shortcut = shell.CreateShortcut(str(lnk_path))
        return {
            "target_path": str(shortcut.Targetpath or ""),
            "arguments": str(shortcut.Arguments or ""),
            "icon_location": str(shortcut.IconLocation or ""),
        }
    except Exception as exc:
        logger.debug("Could not resolve shortcut %s: %s", lnk_path, exc)
        return None


def _match_app(shortcut_name: str, software_entries: List[Dict[str, Any]]) -> str:
    """Best-effort match of a shortcut to an installed application's DisplayName.

    Matches on the shortcut's display name only (not its target exe path) —
    many installers (Discord, GitHub Desktop, Slack) route shortcuts through
    a generic "Update.exe" stub, so matching against the target path produces
    false positives against unrelated apps that happen to share a common word.
    """
    name_norm = _normalize_name(shortcut_name)
    if not name_norm:
        return ""

    best_match = ""
    for entry in software_entries:
        display_name = str(entry.get("DisplayName", ""))
        display_norm = _normalize_name(display_name)
        if not display_norm:
            continue
        if display_norm == name_norm:
            return display_name
        if len(name_norm) >= 4 and len(display_norm) >= 4 and (
            display_norm in name_norm or name_norm in display_norm
        ):
            best_match = best_match or display_name
    return best_match


def collect_shortcuts_inventory(software_entries: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Collect Desktop / Start Menu / Taskbar shortcuts and match them to installed apps.

    Returns an empty entry list on non-Windows platforms or when pywin32
    is unavailable.
    """
    entries: List[Dict[str, Any]] = []

    if _win32com_client is None:
        logger.warning("pywin32 is not available — skipping shortcut collection.")
        return {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "entries": entries,
            "counts": {},
        }

    shell = _win32com_client.Dispatch("WScript.Shell")
    software_entries = software_entries or []
    seen_targets: set[str] = set()

    for category, directory, recursive in _shortcut_dirs():
        if not directory.exists():
            continue
        pattern = "**/*.lnk" if recursive else "*.lnk"
        for lnk_path in directory.glob(pattern):
            resolved = _resolve_shortcut(shell, lnk_path)
            if not resolved or not resolved["target_path"]:
                continue

            dedup_key = f"{category}:{resolved['target_path'].lower()}"
            if dedup_key in seen_targets:
                continue
            seen_targets.add(dedup_key)

            name = lnk_path.stem
            matched_app = _match_app(name, software_entries)

            entries.append({
                "name": name,
                "category": category,
                "target_path": resolved["target_path"],
                "arguments": resolved["arguments"],
                "icon_location": resolved["icon_location"],
                "matched_app": matched_app,
            })

    counts = {
        "desktop": sum(1 for e in entries if e["category"] == "desktop"),
        "start_menu": sum(1 for e in entries if e["category"] == "start_menu"),
        "taskbar": sum(1 for e in entries if e["category"] == "taskbar"),
        "matched": sum(1 for e in entries if e["matched_app"]),
    }

    logger.info(
        "Shortcut inventory collected: %d desktop, %d start menu, %d taskbar (%d matched to an installed app)",
        counts["desktop"], counts["start_menu"], counts["taskbar"], counts["matched"],
    )

    return {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "entries": entries,
        "counts": counts,
    }


def write_shortcuts_inventory(
    config: MigrationConfigRoot,
    inventory: Dict[str, Any],
    filename: str = "shortcuts_inventory.json",
) -> Path:
    """Write the shortcuts inventory to the configured inventory output directory."""
    import json

    out_dir = DATA_DIR / config.source_system.inventory_output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    logger.info("Writing shortcuts inventory to: %s", out_path)
    return out_path
