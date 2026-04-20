"""App-level recommendation engine for Windows-to-Linux mappings."""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.constants import BASE_DIR, CONFIG_DIR


class RecommendationService:
    """Generate Windows application migration recommendations."""

    def __init__(self, reports_dir: Path | None = None) -> None:
        """Create a recommendation service and choose the reports directory."""
        self.map_file = CONFIG_DIR / "linux_ms_map.csv"
        self.reports_dir = reports_dir or (BASE_DIR / "docs" / "reports")

    @staticmethod
    def _normalize_name(value: str) -> str:
        """Normalize an application name for matching and comparison."""
        lowered = value.lower().strip()
        return re.sub(r"[^a-z0-9]+", " ", lowered).strip()

    def _load_mapping_rows(self) -> list[dict[str, str]]:
        """Load the configured Windows-to-Linux mapping CSV file."""
        if not self.map_file.exists():
            return []
        with self.map_file.open("r", encoding="utf-8", newline="") as handle:
            return [row for row in csv.DictReader(handle)]

    def _find_mapping(self, app_name: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
        """Find the best mapping row for a Windows application name."""
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
        """Check whether a package name appears to be available online."""
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
        """Score a recommendation using confidence, category fit, and package visibility."""
        confidence_weight = {"high": 45, "medium": 28, "low": 15}.get(confidence.lower(), 20)
        category_bonus = 12 if category else 0
        online_bonus = 20 if online_signal == "verified" else 6
        return min(100, confidence_weight + category_bonus + online_bonus)

    @staticmethod
    def _confidence_rank(value: str) -> int:
        """Map textual confidence labels to sortable ranks."""
        return {"high": 3, "medium": 2, "low": 1}.get(str(value).lower(), 0)

    def _apply_selection_profile(self, recommendations: list[dict[str, Any]], selection_profile: str) -> list[dict[str, Any]]:
        """Trim or rank recommendations according to the chosen selection profile."""
        if selection_profile != "prioritize":
            return recommendations

        ranked = sorted(
            recommendations,
            key=lambda rec: (
                int(rec.get("agent_score", 0)),
                self._confidence_rank(str(rec.get("mapping_confidence", ""))),
                1 if rec.get("online_signal") == "verified" else 0,
            ),
            reverse=True,
        )
        limit = max(12, int(len(ranked) * 0.4))
        shortlisted = ranked[:limit]
        for idx, rec in enumerate(shortlisted, start=1):
            rec["priority_rank"] = idx
            rec["selection_profile"] = "prioritize"
        return shortlisted

    @staticmethod
    def _ai_enabled() -> bool:
        """Return whether AI ranking can be attempted from environment variables."""
        return bool(os.getenv("AI_RECOMMENDER_ENDPOINT") and os.getenv("AI_RECOMMENDER_MODEL"))

    def _ai_rank_recommendations(
        self,
        recommendations: list[dict[str, Any]],
        selection_profile: str,
    ) -> tuple[list[dict[str, Any]], str]:
        """Ask an AI endpoint to reorder recommendation candidates."""
        endpoint = os.getenv("AI_RECOMMENDER_ENDPOINT", "").strip()
        model = os.getenv("AI_RECOMMENDER_MODEL", "").strip()
        api_key = os.getenv("AI_RECOMMENDER_API_KEY", "").strip()
        if not endpoint or not model:
            return recommendations, "deterministic"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        compact_items = [
            {
                "windows_app": rec.get("windows_app", ""),
                "linux_package": rec.get("linux_package", ""),
                "category": rec.get("category", ""),
                "mapping_confidence": rec.get("mapping_confidence", ""),
                "agent_score": int(rec.get("agent_score", 0)),
            }
            for rec in recommendations
        ]

        prompt = {
            "task": "Rank migration recommendation candidates and explain top priorities.",
            "selection_profile": selection_profile,
            "requirements": [
                "Return strict JSON only.",
                "Preserve windows_app values exactly.",
                "Use keys: ranked_apps, where ranked_apps is a list of objects with windows_app, priority_rank, ai_reason.",
            ],
            "candidates": compact_items,
        }

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a migration recommendation assistant that returns strict JSON."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(endpoint, headers=headers, json=body, timeout=10)
            if response.status_code != 200:
                return recommendations, "deterministic"

            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            data = json.loads(content)
            ranked_apps = data.get("ranked_apps", []) if isinstance(data, dict) else []
            rank_by_name = {
                str(item.get("windows_app", "")): item
                for item in ranked_apps
                if isinstance(item, dict)
            }

            ordered: list[dict[str, Any]] = []
            for rec in recommendations:
                app_name = str(rec.get("windows_app", ""))
                ai_item = rank_by_name.get(app_name)
                if not ai_item:
                    continue
                merged = dict(rec)
                merged["priority_rank"] = int(ai_item.get("priority_rank", 0))
                merged["ai_reason"] = str(ai_item.get("ai_reason", ""))
                ordered.append(merged)

            if not ordered:
                return recommendations, "deterministic"

            ordered.sort(key=lambda item: int(item.get("priority_rank", 10**6)))
            return ordered, "ai_model"
        except Exception:
            return recommendations, "deterministic"

    def generate_recommendations(
        self,
        software_inventory: dict[str, Any],
        strategy: str = "local",
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate app migration recommendations and write report artifacts."""
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

        recommendations = self._apply_selection_profile(recommendations, selection_profile)
        ranking_method = "deterministic"
        if strategy == "agent" and self._ai_enabled() and recommendations:
            recommendations, ranking_method = self._ai_rank_recommendations(
                recommendations=recommendations,
                selection_profile=selection_profile,
            )

        generated_at = datetime.now().isoformat()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.reports_dir / f"software_recommendations_{strategy}_{selection_profile}_{stamp}.json"
        md_path = self.reports_dir / f"software_recommendations_{strategy}_{selection_profile}_{stamp}.md"

        payload = {
            "generated_at": generated_at,
            "strategy": strategy,
            "selection_profile": selection_profile,
            "ranking_method": ranking_method,
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
            f"Selection profile: {selection_profile}",
            f"Ranking method: {ranking_method}",
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
            "selection_profile": selection_profile,
            "ranking_method": ranking_method,
            "recommendations": recommendations,
            "recommended_count": len(recommendations),
            "input_count": len(entries),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }
