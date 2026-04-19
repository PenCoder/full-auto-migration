from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.constants import DATA_DIR


class ProfileService:
    def __init__(self, profile_path: Path | None = None) -> None:
        self.profile_path = profile_path or (DATA_DIR / "profiles" / "active_profile.json")
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.profile_path.exists():
            return {}
        return json.loads(self.profile_path.read_text(encoding="utf-8"))

    def save(self, profile: dict[str, Any]) -> Path:
        self.profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return self.profile_path

    def get_mapping_overrides(self) -> list[dict[str, str]]:
        profile = self.load()
        overrides = profile.get("mapping_overrides", [])
        if isinstance(overrides, list):
            return overrides
        return []
