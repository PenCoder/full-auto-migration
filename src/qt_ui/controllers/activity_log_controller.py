"""Activity log controller for Qt migration window."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class ActivityLogController:
    """Maintain activity entries, filtering, and export formatting."""

    def __init__(self) -> None:
        self.entries: list[dict[str, str]] = []
        self.filters: dict[str, bool] = {
            "info": True,
            "done": True,
            "warn": True,
            "fail": True,
        }

    @staticmethod
    def level_to_badge(level: str) -> str:
        norm = level.lower()
        if norm in {"success", "done"}:
            return "DONE"
        if norm in {"warn", "warning"}:
            return "WARN"
        if norm in {"error", "fail"}:
            return "FAIL"
        return "INFO"

    @staticmethod
    def phase_to_icon(phase: str) -> str:
        return {
            "system": "SYS",
            "pipeline": "PIP",
            "inventory": "INV",
            "analysis": "MAP",
            "backup": "BKP",
            "restore": "RST",
            "validation": "VAL",
            "report": "RPT",
            "recommendations": "REC",
        }.get(phase.lower(), "LOG")

    @staticmethod
    def badge_to_level_key(badge: str) -> str:
        key = badge.lower()
        if key == "done":
            return "done"
        if key == "warn":
            return "warn"
        if key == "fail":
            return "fail"
        return "info"

    def set_filter(self, key: str, enabled: bool) -> None:
        self.filters[key] = enabled

    def append(self, phase: str, message: str, level: str) -> str:
        badge = self.level_to_badge(level)
        icon = self.phase_to_icon(phase)
        ts = datetime.now().strftime("%H:%M:%S")
        self.entries.append(
            {
                "time": ts,
                "badge": badge,
                "icon": icon,
                "phase": phase,
                "message": message,
            }
        )
        return message

    def iter_visible_entries(self):
        for entry in reversed(self.entries):
            badge = entry.get("badge", "INFO")
            level_key = self.badge_to_level_key(badge)
            if self.filters.get(level_key, True):
                yield entry

    def export_session_log(
        self,
        reports_dir: Path,
        runtime_mode: str,
    ) -> tuple[Path, Path]:
        reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = reports_dir / f"session_activity_log_{stamp}.json"
        md_path = reports_dir / f"session_activity_log_{stamp}.md"

        payload = {
            "generated_at": datetime.now().isoformat(),
            "runtime_mode": runtime_mode,
            "entries": self.entries,
        }

        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines = [
            "# Session Activity Log",
            "",
            f"Generated at: {payload['generated_at']}",
            f"Runtime mode: {runtime_mode}",
            "",
            "| Time | Badge | Phase | Message |",
            "|---|---|---|---|",
        ]
        for entry in self.entries:
            lines.append(
                f"| {entry.get('time', '--:--:--')} | {entry.get('badge', 'INFO')} | {entry.get('phase', '').upper()} | {entry.get('message', '').replace('|', '/')} |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return json_path, md_path
