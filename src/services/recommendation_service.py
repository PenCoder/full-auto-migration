"""App-level recommendation engine for Windows-to-Linux mappings."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.analysis.dynamic_rules import resolve_mapping
from src.constants import BASE_DIR, CONFIG_DIR


class RecommendationService:
    """Generate Windows application migration recommendations."""

    # Repositories considered relevant for Linux Mint / Ubuntu-based systems.
    # Repositories that confirm a package is available for the target system (Linux Mint).
    # Linux Mint is Ubuntu/Debian-based; linuxmint_21/22 are the primary targets.
    _TARGET_REPOS = {"linuxmint_21", "linuxmint_22", "ubuntu_22_04", "ubuntu_24_04", "flathub"}

    def __init__(self, reports_dir: Path | None = None) -> None:
        """Create a recommendation service and choose the reports directory."""
        self.map_file = CONFIG_DIR / "linux_ms_map.csv"
        self.reports_dir = reports_dir or (BASE_DIR / "docs" / "reports")
        self._repology_cache: dict[str, dict[str, Any]] = {}

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

    def _query_online_package_signal(self, package_name: str, provider: str = "repology") -> str:
        """Check package availability via Repology, with target-repo parsing and session caching."""
        if not package_name:
            return "unknown"
        if provider != "repology":
            return "not_supported"

        if package_name in self._repology_cache:
            return self._repology_cache[package_name].get("signal", "cached")

        url = f"https://repology.org/api/v1/project/{package_name}"
        try:
            response = requests.get(
                url,
                timeout=6,
                headers={"User-Agent": "semi-automigration/1.0 (migration tool; metadata only)"},
            )
            if response.status_code == 404:
                result = {"signal": "not_found", "repos": []}
                self._repology_cache[package_name] = result
                return "not_found"
            if response.status_code != 200:
                return "not_verified"

            packages = response.json()
            if not isinstance(packages, list):
                return "not_verified"

            # Extract which repositories carry this package.
            repos_found = {
                str(pkg.get("repo", "")).lower()
                for pkg in packages
                if isinstance(pkg, dict) and pkg.get("repo")
            }
            target_hits = repos_found & self._TARGET_REPOS
            signal = "verified" if target_hits else ("available" if repos_found else "not_verified")
            self._repology_cache[package_name] = {
                "signal": signal,
                "repos": sorted(repos_found),
                "target_repos": sorted(target_hits),
            }
            return signal
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
                int(rec.get("repology_score", 0)),
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

    def generate_recommendations(
        self,
        software_inventory: dict[str, Any],
        strategy: str = "local",
        selection_profile: str = "migrate_all",
        repology_config: dict[str, Any] | None = None,
        mapping_overrides: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate app migration recommendations and write report artifacts."""
        cfg = repology_config or {}
        repology_enabled = bool(cfg.get("software_online_lookup_enabled", True))
        provider = str(cfg.get("software_online_provider", "repology")).strip() or "repology"
        allowed_fields = {
            str(f).strip().lower()
            for f in cfg.get("software_online_send_fields", ["name", "version", "publisher"])
            if str(f).strip()
        }

        rows = self._load_mapping_rows()
        entries = software_inventory.get("entries", []) if isinstance(software_inventory, dict) else []
        overrides = mapping_overrides or []

        recommendations: list[dict[str, Any]] = []
        for item in entries:
            app_name = str(item.get("DisplayName") or item.get("name") or "").strip()
            if not app_name:
                continue

            decision = resolve_mapping(app_name, rows, overrides=overrides)
            if not decision:
                continue

            package_name = decision.linux_package

            score = decision.confidence_score
            if score >= 0.9:
                confidence_label = "high"
            elif score >= 0.7:
                confidence_label = "medium"
            else:
                confidence_label = "low"

            # "online" strategy queries Repology for package availability signals.
            online_signal = "not_checked"
            if strategy == "online":
                if not repology_enabled:
                    online_signal = "policy_blocked"
                elif "name" in allowed_fields:
                    online_signal = self._query_online_package_signal(package_name, provider=provider)
                else:
                    online_signal = "policy_blocked"

            recommendation: dict[str, Any] = {
                "windows_app": app_name,
                "linux_package": package_name,
                "linux_display_name": decision.linux_display_name,
                "category": decision.category,
                "migration_strategy": decision.migration_strategy,
                "mapping_confidence": confidence_label,
                "mapping_source": decision.recommendation_source,
                "notes": decision.notes,
                "online_signal": online_signal,
                "source": strategy,
            }

            if strategy == "online":
                recommendation["repology_score"] = self._agent_score(
                    confidence=confidence_label,
                    category=decision.category,
                    online_signal=online_signal,
                )

            recommendations.append(recommendation)

        recommendations = self._apply_selection_profile(recommendations, selection_profile)

        generated_at = datetime.now().isoformat()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.reports_dir / f"software_recommendations_{strategy}_{selection_profile}_{stamp}.json"
        md_path = self.reports_dir / f"software_recommendations_{strategy}_{selection_profile}_{stamp}.md"

        payload = {
            "generated_at": generated_at,
            "strategy": strategy,
            "selection_profile": selection_profile,
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
            f"Matched applications: {len(recommendations)} / {len(entries)}",
            "",
            "| Windows App | Linux Package | Category | Confidence | Online |",
            "|---|---|---|---|---|",
        ]
        for rec in recommendations:
            lines.append(
                f"| {rec.get('windows_app', '')} | {rec.get('linux_package', '')} | {rec.get('category', '')} | {rec.get('mapping_confidence', '')} | {rec.get('online_signal', '')} |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return {
            "strategy": strategy,
            "selection_profile": selection_profile,
            "recommendations": recommendations,
            "recommended_count": len(recommendations),
            "input_count": len(entries),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }
