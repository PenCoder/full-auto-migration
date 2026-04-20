"""File-level recommendation engine for migration scope and priority."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.constants import BASE_DIR, CONFIG_DIR


class FileRecommendationService:
    """Generate file-level migration recommendations based on scan data and user preference."""

    def __init__(self, reports_dir: Path | None = None) -> None:
        """Create the service and choose the output directory for reports."""
        self.reports_dir = reports_dir or (BASE_DIR / "docs" / "reports")

    @staticmethod
    def _classify_file_importance(
        file_path: str,
        file_size: int,
        extension: str,
        last_accessed_days_ago: int | None = None,
    ) -> str:
        """Heuristically classify file importance: critical, important, useful, or low."""
        # Critical: config, database, source code, keys
        critical_patterns = [
            r"\.conf$", r"\.config$", r"\.cfg$",
            r"\.db$", r"\.sqlite$",
            r"\.py$", r"\.js$", r"\.java$", r"\.cpp$", r"\.c$",
            r"\.key$", r"\.pem$", r"\.gpg$",
        ]
        if any(re.search(pattern, file_path.lower()) for pattern in critical_patterns):
            return "critical"

        # Important: documents, images, videos from recent use
        important_exts = [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"]
        if any(file_path.lower().endswith(ext) for ext in important_exts):
            if last_accessed_days_ago is None or last_accessed_days_ago < 90:
                return "important"

        # Useful: recently accessed or moderate size
        if last_accessed_days_ago is not None and last_accessed_days_ago < 30:
            return "important"
        if 1_000_000 < file_size < 500_000_000:  # 1MB to 500MB
            return "useful"

        # Low: old files, small junk, or rarely-used
        if last_accessed_days_ago is not None and last_accessed_days_ago > 365:
            return "low"
        return "low"

    @staticmethod
    def _confidence_rank(value: str) -> int:
        """Map importance labels to sortable ranks."""
        return {"critical": 4, "important": 3, "useful": 2, "low": 1}.get(str(value).lower(), 0)

    def _apply_choice_mode(
        self,
        recommendations: list[dict[str, Any]],
        choice_mode: str,
    ) -> list[dict[str, Any]]:
        """Filter and reorder recommendations based on user data choice mode."""
        if choice_mode == "manual":
            # User will handle manually; return empty shortlist
            return []

        if choice_mode == "all_files":
            # Include all; sort by importance
            return sorted(
                recommendations,
                key=lambda rec: (
                    self._confidence_rank(str(rec.get("importance", "low"))),
                    int(rec.get("file_size", 0)),
                ),
                reverse=True,
            )

        if choice_mode == "selected_types":
            # Whitelist by extension; let UI let user select types
            return recommendations

        if choice_mode == "ai_recommended":
            # Rely on AI to prioritize; keep full set for AI to rank
            return recommendations

        return recommendations

    @staticmethod
    def _ai_enabled() -> bool:
        """Return whether AI ranking can be attempted from environment variables."""
        return bool(os.getenv("AI_RECOMMENDER_ENDPOINT") and os.getenv("AI_RECOMMENDER_MODEL"))

    def _ai_rank_files(
        self,
        recommendations: list[dict[str, Any]],
        choice_mode: str,
    ) -> tuple[list[dict[str, Any]], str]:
        """Use AI to rank files by migration priority and explain reasoning."""
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
                "file_path": rec.get("file_path", ""),
                "file_size": int(rec.get("file_size", 0)),
                "extension": rec.get("extension", ""),
                "importance": rec.get("importance", "low"),
                "last_accessed_days_ago": rec.get("last_accessed_days_ago"),
            }
            for rec in recommendations
        ]

        prompt = {
            "task": "Prioritize files for migration to Linux based on importance and usage.",
            "choice_mode": choice_mode,
            "requirements": [
                "Return strict JSON only.",
                "Preserve file_path values exactly.",
                "Use keys: ranked_files, where ranked_files is a list of objects with file_path, priority_rank, ai_reason.",
            ],
            "candidates": compact_items,
        }

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a file migration priority assistant that returns strict JSON."},
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
            ranked_files = data.get("ranked_files", []) if isinstance(data, dict) else []

            rank_by_path = {
                str(item.get("file_path", "")): item
                for item in ranked_files
                if isinstance(item, dict)
            }

            ordered: list[dict[str, Any]] = []
            for rec in recommendations:
                file_path = str(rec.get("file_path", ""))
                ai_item = rank_by_path.get(file_path)
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
        file_inventory: dict[str, Any],
        choice_mode: str = "all_files",
        use_ai: bool = False,
        ai_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate file-level recommendations and write report artifacts."""
        # If user chose manual, return empty set
        if choice_mode == "manual":
            return {
                "choice_mode": choice_mode,
                "ranking_method": "skipped",
                "recommendations": [],
                "recommended_count": 0,
                "input_count": 0,
                "json_path": "",
                "markdown_path": "",
            }

        entries = file_inventory.get("files", []) if isinstance(file_inventory, dict) else []
        recommendations: list[dict[str, Any]] = []

        for item in entries:
            file_path = str(item.get("path", ""))
            if not file_path:
                continue

            extension = Path(file_path).suffix or "unknown"
            file_size = int(item.get("size", 0))
            last_accessed_days = item.get("last_accessed_days_ago")

            importance = self._classify_file_importance(
                file_path=file_path,
                file_size=file_size,
                extension=extension,
                last_accessed_days_ago=last_accessed_days,
            )

            recommendation: dict[str, Any] = {
                "file_path": file_path,
                "extension": extension,
                "file_size": file_size,
                "importance": importance,
                "last_accessed_days_ago": last_accessed_days,
                "migrate": importance in {"critical", "important"},  # Default decision
            }
            recommendations.append(recommendation)

        # Apply choice mode selection
        recommendations = self._apply_choice_mode(recommendations, choice_mode)

        ranking_method = "deterministic"
        if use_ai and choice_mode == "ai_recommended" and recommendations:
            try:
                recommendations, ranking_method = self._ai_rank_files(
                    recommendations=recommendations,
                    choice_mode=choice_mode,
                )
            except Exception:
                pass

        generated_at = datetime.now().isoformat()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.reports_dir / f"file_recommendations_{choice_mode}_{stamp}.json"
        md_path = self.reports_dir / f"file_recommendations_{choice_mode}_{stamp}.md"

        payload = {
            "generated_at": generated_at,
            "choice_mode": choice_mode,
            "ranking_method": ranking_method,
            "input_count": len(entries),
            "recommended_count": len(recommendations),
            "recommendations": recommendations,
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        lines = [
            "# File Migration Recommendations",
            "",
            f"Generated at: {generated_at}",
            f"Choice mode: {choice_mode}",
            f"Ranking method: {ranking_method}",
            f"Selected files: {len(recommendations)} / {len(entries)}",
            "",
            "| File Path | Size (MB) | Importance | Migrate |",
            "|---|---|---|---|",
        ]
        for rec in recommendations:
            size_mb = int(rec.get("file_size", 0)) / (1024 * 1024)
            migrate_str = "Yes" if rec.get("migrate") else "No"
            lines.append(
                f"| {rec.get('file_path', '')} | {size_mb:.1f} | {rec.get('importance', '')} | {migrate_str} |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return {
            "choice_mode": choice_mode,
            "ranking_method": ranking_method,
            "recommendations": recommendations,
            "recommended_count": len(recommendations),
            "input_count": len(entries),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }
