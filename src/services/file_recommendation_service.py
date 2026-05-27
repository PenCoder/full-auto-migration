"""File-level recommendation engine for migration scope and priority."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

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
        selected_file_types: dict[str, bool] | None = None,
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
            selected = {
                str(ext).lower()
                for ext, enabled in (selected_file_types or {}).items()
                if bool(enabled)
            }
            if not selected:
                return []
            return [
                rec for rec in recommendations
                if str(rec.get("extension", "")).lower() in selected
            ]

        return recommendations

    def generate_recommendations(
        self,
        file_inventory: dict[str, Any],
        choice_mode: str = "all_files",
        selected_file_types: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Generate file-level recommendations and write report artifacts."""
        if choice_mode == "manual":
            return {
                "choice_mode": choice_mode,
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

            recommendations.append({
                "file_path": file_path,
                "extension": extension,
                "file_size": file_size,
                "importance": importance,
                "last_accessed_days_ago": last_accessed_days,
                "migrate": importance in {"critical", "important"},
            })

        recommendations = self._apply_choice_mode(
            recommendations,
            choice_mode,
            selected_file_types=selected_file_types,
        )

        generated_at = datetime.now().isoformat()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.reports_dir / f"file_recommendations_{choice_mode}_{stamp}.json"
        md_path = self.reports_dir / f"file_recommendations_{choice_mode}_{stamp}.md"

        payload = {
            "generated_at": generated_at,
            "choice_mode": choice_mode,
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
            "recommendations": recommendations,
            "recommended_count": len(recommendations),
            "input_count": len(entries),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }
