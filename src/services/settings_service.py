"""Settings migration planning for wallpapers, themes, and desktop preferences."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.constants import BASE_DIR


class SettingsMigrationService:
    """Build a mode-aware migration plan from a settings inventory snapshot."""

    def build_plan(
        self,
        inventory: dict[str, Any],
        mode: str,
        selections: dict[str, bool] | None = None,
        migrate_enabled: bool = True,
        shortcuts_inventory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Translate a settings inventory into auto/suggest/manual migration actions."""
        desktop = inventory.get("desktop", {}) if isinstance(inventory, dict) else {}
        appearance = inventory.get("appearance", {}) if isinstance(inventory, dict) else {}
        exported_assets = inventory.get("exported_assets", {}) if isinstance(inventory, dict) else {}
        selected_items = selections if isinstance(selections, dict) else {}

        wallpaper_path = str(desktop.get("wallpaper_path", "")).strip()
        theme_path = str(appearance.get("current_theme", "")).strip()
        light_theme = appearance.get("apps_use_light_theme")
        system_light_theme = appearance.get("system_uses_light_theme")
        accent_color = appearance.get("accent_color")

        normalized_mode = mode.lower().strip()
        items: list[dict[str, Any]] = []

        if not migrate_enabled:
            return {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "mode": normalized_mode,
                "customization_depth": "disabled",
                "summary": "Settings migration is disabled for this session.",
                "items": [],
                "counts": {"auto_migrate": 0, "suggest_review": 0, "manual_review": 0, "excluded": 0},
                "exported_assets": exported_assets if isinstance(exported_assets, dict) else {},
            }

        if wallpaper_path:
            items.append(
                self._make_item(
                    name="Wallpaper",
                    source_value=wallpaper_path,
                    mode=normalized_mode,
                    selected=selected_items.get("wallpaper", True),
                    auto_modes={"guided", "balanced", "expert"},
                    suggest_modes=set(),
                    notes="Portable asset exported separately when available.",
                )
            )

        if theme_path:
            items.append(
                self._make_item(
                    name="Theme File",
                    source_value=theme_path,
                    mode=normalized_mode,
                    selected=selected_items.get("theme", True),
                    auto_modes={"expert"},
                    suggest_modes={"guided", "balanced"},
                    notes="Theme references may need desktop-environment-specific adjustment.",
                )
            )

        if light_theme is not None or system_light_theme is not None:
            items.append(
                self._make_item(
                    name="Light/Dark Preference",
                    source_value=f"apps={light_theme}, system={system_light_theme}",
                    mode=normalized_mode,
                    selected=selected_items.get("light_dark", True),
                    auto_modes=set(),
                    suggest_modes={"guided", "balanced", "expert"},
                    notes="Apply as a recommendation because desktop environments map this differently.",
                )
            )

        if accent_color is not None:
            items.append(
                self._make_item(
                    name="Accent Color",
                    source_value=str(accent_color),
                    mode=normalized_mode,
                    selected=selected_items.get("accent_color", True),
                    auto_modes=set(),
                    suggest_modes={"guided", "balanced", "expert"},
                    notes="Useful for visual continuity, but should be reviewed on the Linux target.",
                )
            )

        shortcuts_count = 0
        if isinstance(shortcuts_inventory, dict):
            counts = shortcuts_inventory.get("counts", {})
            if isinstance(counts, dict):
                shortcuts_count = int(counts.get("matched", 0))

        items.append(
            self._make_item(
                name="App Shortcuts",
                source_value=f"{shortcuts_count} matched shortcut(s)" if shortcuts_count else "Desktop / Start Menu / Taskbar",
                mode=normalized_mode,
                selected=selected_items.get("taskbar_layout", True),
                auto_modes={"guided", "balanced", "expert"},
                suggest_modes=set(),
                notes="Recreates Desktop icons and Start Menu / taskbar launchers for apps with a matched Linux package.",
            )
        )

        if normalized_mode == "expert":
            items.extend(
                [
                    self._manual_item(
                        "Keyboard Shortcuts",
                        "Requires user review and environment-specific mapping.",
                        selected=selected_items.get("keyboard_shortcuts", False),
                    ),
                    self._manual_item(
                        "File Associations",
                        "Can be recreated, but deserves explicit confirmation.",
                        selected=selected_items.get("file_associations", False),
                    ),
                ]
            )

        if normalized_mode == "guided":
            depth = "minimal"
            summary = "Safe defaults with wallpaper and visual identity selected for migration."
        elif normalized_mode == "balanced":
            depth = "standard"
            summary = "Broader customization with user-controlled appearance selections."
        else:
            depth = "advanced"
            summary = "Full control with explicit review points for desktop look and feel preferences."

        counts = {
            "auto_migrate": sum(1 for item in items if item["action"] == "auto_migrate"),
            "suggest_review": sum(1 for item in items if item["action"] == "suggest_review"),
            "manual_review": sum(1 for item in items if item["action"] == "manual_review"),
            "excluded": sum(1 for item in items if item["action"] == "exclude"),
        }

        return {
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "mode": normalized_mode,
            "customization_depth": depth,
            "summary": summary,
            "items": items,
            "counts": counts,
            "exported_assets": exported_assets if isinstance(exported_assets, dict) else {},
        }

    def write_plan(
        self,
        plan: dict[str, Any],
        report_dir: Path | None = None,
        basename: str = "settings_migration_plan",
    ) -> dict[str, str]:
        """Write the plan as JSON and Markdown evidence files."""
        output_dir = report_dir or (BASE_DIR / "docs" / "reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / f"{basename}.json"
        md_path = output_dir / f"{basename}.md"

        json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        md_path.write_text(self._render_markdown(plan), encoding="utf-8")
        return {"json_path": str(json_path), "markdown_path": str(md_path)}

    @staticmethod
    def _make_item(
        *,
        name: str,
        source_value: str,
        mode: str,
        selected: bool,
        auto_modes: set[str],
        suggest_modes: set[str],
        notes: str,
    ) -> dict[str, Any]:
        if not selected:
            action = "exclude"
            confidence = "low"
        elif mode in auto_modes:
            action = "auto_migrate"
            confidence = "high"
        elif mode in suggest_modes:
            action = "suggest_review"
            confidence = "medium"
        else:
            action = "manual_review"
            confidence = "low"
        return {
            "name": name,
            "source_value": source_value,
            "action": action,
            "confidence": confidence,
            "notes": notes,
        }

    @staticmethod
    def _manual_item(name: str, notes: str, selected: bool = True) -> dict[str, Any]:
        return {
            "name": name,
            "source_value": "",
            "action": "manual_review" if selected else "exclude",
            "confidence": "low",
            "notes": notes,
        }

    @staticmethod
    def _render_markdown(plan: dict[str, Any]) -> str:
        lines = [
            "# Settings Migration Plan",
            "",
            f"Generated at: {plan.get('generated_at', '')}",
            f"Mode: {plan.get('mode', '')}",
            f"Customization depth: {plan.get('customization_depth', '')}",
            f"Summary: {plan.get('summary', '')}",
            "",
            "| Setting | Action | Confidence | Notes |",
            "|---|---|---|---|",
        ]
        for item in plan.get("items", []):
            lines.append(
                f"| {item.get('name', '')} | {item.get('action', '')} | {item.get('confidence', '')} | {item.get('notes', '').replace('|', '/')} |"
            )
        lines.append("")
        return "\n".join(lines)