"""File recommendation service for migration planning."""

from __future__ import annotations

from typing import Any
from src.loggers import get_logger


class FileRecommendationService:
    """Service for generating file migration recommendations.
    
    Responsibilities:
    - Classify files by importance (critical, important, useful, low)
    - Generate recommendations based on file types and paths
    - Support different selection profiles (migrate_all vs. prioritize)
    - Estimate data volume
    """

    def __init__(self, config: Any):
        """Initialize file recommendation service.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.recommendations.file")

    def generate(
        self,
        selected_paths: list[str],
        selection_profile: str = "migrate_all",
    ) -> dict[str, Any]:
        """Generate file migration recommendations.
        
        Args:
            selected_paths: List of file paths to analyze
            selection_profile: "migrate_all" or "prioritize"
            
        Returns:
            Dictionary with file recommendations
        """
        self.logger.info("Generating file recommendations for %d paths", len(selected_paths))
        try:
            recommendations = self._classify_files(selected_paths)
            
            # Apply selection profile
            if selection_profile == "prioritize":
                recommendations = self._prioritize_files(recommendations)
            
            # Calculate statistics
            total_files = len(recommendations)
            critical = len([f for f in recommendations if f.get("priority") == "critical"])
            important = len([f for f in recommendations if f.get("priority") == "important"])
            
            self.logger.info("Generated recommendations for %d files", total_files)
            return {
                "recommendations": recommendations,
                "total_files": total_files,
                "critical_count": critical,
                "important_count": important,
                "selection_profile": selection_profile,
            }
        except Exception as exc:
            self.logger.exception("File recommendation generation failed: %s", exc)
            raise

    def _classify_files(self, paths: list[str]) -> list[dict[str, Any]]:
        """Classify files by importance and priority."""
        recommendations = []
        
        for path in paths:
            priority = self._determine_priority(path)
            recommendations.append({
                "path": path,
                "priority": priority,
                "recommendation": self._get_recommendation(priority),
            })
        
        return recommendations

    @staticmethod
    def _determine_priority(path: str) -> str:
        """Determine file/folder priority based on path patterns."""
        path_lower = path.lower()
        
        # Critical paths
        critical_patterns = ["documents", "desktop", ".ssh", ".pgp"]
        for pattern in critical_patterns:
            if pattern in path_lower:
                return "critical"
        
        # Important paths
        important_patterns = ["downloads", "pictures", "videos", "music", ".config"]
        for pattern in important_patterns:
            if pattern in path_lower:
                return "important"
        
        # Useful paths
        useful_patterns = [".local", "application data", "appdata"]
        for pattern in useful_patterns:
            if pattern in path_lower:
                return "useful"
        
        return "low"

    @staticmethod
    def _get_recommendation(priority: str) -> str:
        """Get recommendation text based on priority."""
        return {
            "critical": "Recommended for migration - contains important user data",
            "important": "Consider migrating - contains user media and documents",
            "useful": "Optional - contains application configurations",
            "low": "Low priority - system files and temporary data",
        }.get(priority, "Unknown priority")

    @staticmethod
    def _prioritize_files(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter files by priority when using prioritize profile."""
        # Keep critical and important files
        priority_order = {"critical": 0, "important": 1, "useful": 2, "low": 3}
        
        filtered = [
            f for f in recommendations
            if priority_order.get(f.get("priority", "low"), 99) <= 1
        ]
        
        # Sort by priority
        filtered.sort(key=lambda f: priority_order.get(f.get("priority", "low"), 99))
        
        return filtered
