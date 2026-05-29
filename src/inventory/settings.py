"""Windows settings and desktop personalization inventory collection."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import MigrationConfigRoot
from src.constants import BASE_DIR, DATA_DIR
from src.loggers import get_logger


logger = get_logger("inventory.settings")


def _run_powershell_json(command: str) -> Any:
    """Run a PowerShell command that returns JSON and decode the result."""
    full_command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]

    try:
        result = subprocess.run(full_command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("PowerShell executable not found in PATH.") from exc

    if result.returncode != 0:
        raise RuntimeError(f"PowerShell command failed with exit code {result.returncode}")

    stdout = (result.stdout or "").strip()
    if not stdout:
        return None
    return json.loads(stdout)


def _normalize_path(value: str | None) -> Path | None:
    if not value:
        return None
    expanded = Path(value).expanduser()
    return expanded if expanded.exists() else None


def _export_asset(source: Path | None, destination_dir: Path, label: str) -> str:
    if source is None or not source.exists() or not source.is_file():
        return ""

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{label}{source.suffix.lower()}"
    shutil.copy2(source, destination)
    return str(destination)


def _read_registry_object(path: str, properties: list[str]) -> dict[str, Any]:
    if not properties:
        return {}

    props = ",".join(properties)
    command = (
        f"Get-ItemProperty -Path '{path}' -ErrorAction SilentlyContinue | "
        f"Select-Object {props} | ConvertTo-Json -Depth 4"
    )

    try:
        data = _run_powershell_json(command)
    except Exception:
        return {}

    if isinstance(data, dict):
        return data
    return {}


def collect_settings_inventory(export_assets: bool = True) -> Dict[str, Any]:
    """Collect Windows settings and appearance inventory.

    The returned structure is intentionally compact and portable:
    it captures only the settings that can be meaningfully inspected,
    summarized, or exported during a migration workflow.
    """
    desktop = _read_registry_object(
        r"HKCU:\Control Panel\Desktop",
        ["WallPaper", "WallpaperStyle", "TileWallpaper"],
    )
    personalize = _read_registry_object(
        r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ["AppsUseLightTheme", "SystemUsesLightTheme"],
    )
    theme = _read_registry_object(
        r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes",
        ["CurrentTheme"],
    )
    dwm = _read_registry_object(
        r"HKCU:\Software\Microsoft\Windows\DWM",
        ["ColorizationColor"],
    )

    wallpaper_path = _normalize_path(str(desktop.get("WallPaper", "")))
    theme_path = _normalize_path(str(theme.get("CurrentTheme", "")))

    assets_dir = BASE_DIR / "docs" / "reports" / "settings_assets"
    exported_assets = {
        "wallpaper": _export_asset(wallpaper_path, assets_dir, "wallpaper") if export_assets else "",
        "theme": _export_asset(theme_path, assets_dir, "current_theme") if export_assets else "",
    }

    desktop_summary = {
        "wallpaper_path": str(wallpaper_path) if wallpaper_path else "",
        "wallpaper_style": str(desktop.get("WallpaperStyle", "")),
        "tile_wallpaper": str(desktop.get("TileWallpaper", "")),
    }
    appearance_summary = {
        "current_theme": str(theme.get("CurrentTheme", "")),
        "apps_use_light_theme": personalize.get("AppsUseLightTheme"),
        "system_uses_light_theme": personalize.get("SystemUsesLightTheme"),
        "accent_color": dwm.get("ColorizationColor"),
    }

    summary = {
        "portable_items": sum(1 for value in [wallpaper_path, theme_path] if value is not None),
        "exported_items": sum(1 for value in exported_assets.values() if value),
    }

    return {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "desktop": desktop_summary,
        "appearance": appearance_summary,
        "exported_assets": exported_assets,
        "summary": summary,
    }


def write_settings_inventory(
    config: MigrationConfigRoot,
    inventory: Dict[str, Any],
    filename: str = "settings_inventory.json",
) -> Path:
    """Write the settings inventory to the configured inventory output directory."""
    out_dir = DATA_DIR / config.source_system.inventory_output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    logger.info("Writing settings inventory to: %s", out_path)
    return out_path