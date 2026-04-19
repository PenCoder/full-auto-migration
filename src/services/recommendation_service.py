from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.constants import BASE_DIR, CONFIG_DIR


class RecommendationService:
    def __init__(self, reports_dir: Path | None = None) -> None:
        self.map_file = CONFIG_DIR / "linux_ms_map.csv"
        self.reports_dir = reports_dir or (BASE_DIR / "docs" / "reports")

    @staticmethod
    def _normalize_name(value: str) -> str:
        lowered = value.lower().strip()
        return re.sub(r"[^a-z0-9]+", " ", lowered).strip()

    def _load_mapping_rows(self) -> list[dict[str, str]]:
        if not self.map_file.exists():
            return []
        with self.map_file.open("r", encoding="utf-8", newline="") as handle:
            return [row for row in csv.DictReader(handle)]

    def _find_mapping(self, app_name: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
        app_norm = self._normalize_name(app_name)
        for row in rows:
            win_name = row.get("windows_name", "")
            win_norm = self._normalize_name(win_name)
            if not win_norm:
                continue
            if win_norm in app_norm or app_norm in win_norm:
                return row
        return None

    def _query_online_package_signal(self, package_name: str) -> str:
        if not package_name:
            return "unknown"
        url = f"https://repology.org/api/v1/project/{package_name}"
        try:
            response = requests.get(url, timeout=4)
            if response.status_code != 200:
                return "not_verified"
            payload = response.json()
            if isinstance(payload, dict) and payload:
                return "verified"
            return "not_verified"
        except Exception:
            return "unreachable"

    @staticmethod
    def _agent_score(confidence: str, category: str, online_signal: str) -> int:
        confidence_weight = {"high": 45, "medium": 28, "low": 15}.get(confidence.lower(), 20)
        category_bonus = 12 if category else 0
        online_bonus = 20 if online_signal == "verified" else 6
        return min(100, confidence_weight + category_bonus + online_bonus)

    def generate_recommendations(
        self,
        software_inventory: dict[str, Any],
        strategy: str = "local",
    ) -> dict[str, Any]:
        rows = self._load_mapping_rows()
        entries = software_inventory.get("entries", []) if isinstance(software_inventory, dict) else []

        recommendations: list[dict[str, Any]] = []
        for item in entries:
            app_name = str(item.get("DisplayName") or item.get("name") or "").strip()
            if not app_name:
                continue

            mapped = self._find_mapping(app_name, rows)
            if not mapped:
                continue

            package_name = mapped.get("linux_package", "")
            online_signal = "not_checked"
            if strategy in {"online", "agent"}:
                online_signal = self._query_online_package_signal(package_name)

            recommendation: dict[str, Any] = {
                "windows_app": app_name,
                "linux_package": package_name,
                "linux_display_name": mapped.get("linux_display_name", ""),
                "category": mapped.get("category", ""),
                "migration_strategy": mapped.get("migration_strategy", ""),
                "mapping_confidence": mapped.get("confidence", ""),
                "notes": mapped.get("notes", ""),
                "online_signal": online_signal,
                "source": strategy,
            }

            if strategy == "agent":
                score = self._agent_score(
                    confidence=recommendation.get("mapping_confidence", ""),
                    category=recommendation.get("category", ""),
                    online_signal=online_signal,
                )
                recommendation["agent_score"] = score
                recommendation["agent_reason"] = (
                    "Agent strategy prioritized confidence, category fit, and package visibility signals."
                )

            recommendations.append(recommendation)

        generated_at = datetime.now().isoformat()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.reports_dir / f"software_recommendations_{strategy}_{stamp}.json"
        md_path = self.reports_dir / f"software_recommendations_{strategy}_{stamp}.md"

        payload = {
            "generated_at": generated_at,
            "strategy": strategy,
            "input_count": len(entries),
            "recommended_count": len(recommendations),
            "recommendations": recommendations,
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        lines = [
            "# Software Recommendations",
            "",
            f"Generated at: {generated_at}",
            f"Strategy: {strategy}",
            f"Matched applications: {len(recommendations)} / {len(entries)}",
            "",
            "| Windows App | Linux Package | Confidence | Online |",
            "|---|---|---|---|",
        ]
        for rec in recommendations:
            lines.append(
                f"| {rec.get('windows_app', '')} | {rec.get('linux_package', '')} | {rec.get('mapping_confidence', '')} | {rec.get('online_signal', '')} |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return {
            "strategy": strategy,
            "recommendations": recommendations,
            "recommended_count": len(recommendations),
            "input_count": len(entries),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }
