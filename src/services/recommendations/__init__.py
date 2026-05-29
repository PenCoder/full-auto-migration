"""Recommendation service modules."""

from __future__ import annotations

from src.services.recommendations.app_recommender import AppRecommendationService
from src.services.recommendations.file_recommender import FileRecommendationService

__all__ = [
    "AppRecommendationService",
    "FileRecommendationService",
]
