"""Refactored recommendation services for apps and files."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import requests

from src.loggers import get_logger
from src.constants import CONFIG_DIR


class AppRecommendationService:
    """Service for generating Windows-to-Linux application recommendations.
    
    Responsibilities:
    - Load Windows-to-Linux mapping database
    - Match installed apps to available Linux alternatives
    - Score recommendations by confidence and availability
    - Filter by selection profile (migrate_all vs. prioritize)
    """

    def __init__(self, config: Any):
        """Initialize app recommendation service.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.recommendations.app")
        self.map_file = CONFIG_DIR / "linux_ms_map.csv"

    def generate(
        self,
        software_inventory: dict[str, Any],
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate application migration recommendations.
        
        Args:
            software_inventory: Software inventory from SoftwareInventoryService
            selection_profile: "migrate_all" or "prioritize"
            
        Returns:
            Dictionary with recommended apps and details
        """
        self.logger.info("Generating application recommendations...")
        try:
            entries = software_inventory.get("entries", [])
            recommendations = []
            
            # Load mapping database
            mapping_rows = self._load_mapping_rows()
            
            # Process each installed app
            for entry in entries:
                app_name = entry.get("name", "")
                mapping = self._find_mapping(app_name, mapping_rows)
                
                if mapping:
                    # Score the recommendation
                    confidence = mapping.get("confidence", "low")
                    linux_package = mapping.get("linux_package", "")
                    online_signal = self._query_package_availability(linux_package)
                    agent_score = self._score_recommendation(confidence, mapping.get("category", ""), online_signal)
                    
                    recommendations.append({
                        "windows_app": app_name,
                        "linux_package": linux_package,
                        "mapping_confidence": confidence,
                        "category": mapping.get("category", ""),
                        "online_signal": online_signal,
                        "agent_score": agent_score,
                    })
            
            # Apply selection profile
            recommendations = self._apply_selection_profile(recommendations, selection_profile)
            
            self.logger.info("Generated %d recommendations", len(recommendations))
            return {
                "recommendations": recommendations,
                "total_apps_analyzed": len(entries),
                "total_recommendations": len(recommendations),
                "selection_profile": selection_profile,
            }
        except Exception as exc:
            self.logger.exception("App recommendation generation failed: %s", exc)
            raise

    @staticmethod
    def _normalize_name(value: str) -> str:
        """Normalize an application name for matching."""
        lowered = value.lower().strip()
        return re.sub(r"[^a-z0-9]+", " ", lowered).strip()

    def _load_mapping_rows(self) -> list[dict[str, str]]:
        """Load Windows-to-Linux mapping CSV file."""
        if not self.map_file.exists():
            self.logger.warning("Mapping file not found: %s", self.map_file)
            return []
        
        with self.map_file.open("r", encoding="utf-8", newline="") as handle:
            return [row for row in csv.DictReader(handle)]

    def _find_mapping(self, app_name: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
        """Find best mapping for an application name."""
        app_norm = self._normalize_name(app_name)
        for row in rows:
            win_name = row.get("windows_name", "")
            win_norm = self._normalize_name(win_name)
            if not win_norm:
                continue
            if win_norm in app_norm or app_norm in win_norm:
                return row
        return None

    def _query_package_availability(self, package_name: str) -> str:
        """Check if a Linux package is available online."""
        if not package_name:
            return "unknown"
        
        try:
            url = f"https://repology.org/api/v1/project/{package_name}"
            response = requests.get(url, timeout=4)
            if response.status_code != 200:
                return "not_verified"
            payload = response.json()
            return "verified" if payload else "not_verified"
        except Exception:
            return "unreachable"

    @staticmethod
    def _score_recommendation(confidence: str, category: str, online_signal: str) -> int:
        """Score a recommendation based on multiple factors."""
        confidence_weight = {"high": 45, "medium": 28, "low": 15}.get(confidence.lower(), 20)
        category_bonus = 12 if category else 0
        online_bonus = 20 if online_signal == "verified" else 6
        return min(100, confidence_weight + category_bonus + online_bonus)

    @staticmethod
    def _confidence_rank(value: str) -> int:
        """Map confidence to sortable rank."""
        return {"high": 3, "medium": 2, "low": 1}.get(str(value).lower(), 0)

    def _apply_selection_profile(
        self,
        recommendations: list[dict[str, Any]],
        selection_profile: str,
    ) -> list[dict[str, Any]]:
        """Filter/rank recommendations by selection profile."""
        if selection_profile != "prioritize":
            return recommendations
        
        # Sort by score and confidence
        ranked = sorted(
            recommendations,
            key=lambda rec: (
                int(rec.get("agent_score", 0)),
                self._confidence_rank(rec.get("mapping_confidence", "")),
                1 if rec.get("online_signal") == "verified" else 0,
            ),
            reverse=True,
        )
        
        # Keep top 40% or at least 12 items
        limit = max(12, int(len(ranked) * 0.4))
        shortlisted = ranked[:limit]
        
        for idx, rec in enumerate(shortlisted, start=1):
            rec["priority_rank"] = idx
            rec["selection_profile"] = "prioritize"
        
        return shortlisted
