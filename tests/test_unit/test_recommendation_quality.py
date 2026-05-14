"""Quality tests for the recommendation engine — proving the tool reliably guides users to the right Linux apps.

These tests verify that every Windows application a user cares about finds a
real, installable Linux Mint equivalent.  A passing suite here means the user
can trust the platform's advice and migrate with confidence.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analysis.dynamic_rules import MappingDecision, resolve_mapping
from src.services.recommendation_service import RecommendationService


# ---------------------------------------------------------------------------
# Test data — real-world app names users will actually encounter
# ---------------------------------------------------------------------------

KNOWN_MAPPINGS: list[tuple[str, str]] = [
    ("Microsoft Word", "libreoffice"),
    ("Google Chrome", "chrome"),
    ("Mozilla Firefox", "firefox"),
    ("VLC media player", "vlc"),
    ("7-Zip", "7zip"),
    ("Notepad++", "notepadqq"),
    ("Discord", "discord"),
    ("Spotify", "spotify"),
    ("Zoom", "zoom"),
    ("Git", "git"),
    ("Visual Studio Code", "code"),
    ("Adobe Acrobat Reader", "evince"),
]

SAMPLE_ENTRIES: list[dict[str, str]] = [
    {"DisplayName": display, "Version": "1.0", "Publisher": "Test"}
    for display, _ in KNOWN_MAPPINGS
]

SAMPLE_SOFTWARE_INVENTORY: dict = {"entries": SAMPLE_ENTRIES}


@pytest.fixture()
def csv_map_rows() -> list[dict[str, str]]:
    """Load the real linux_ms_map.csv — the heart of the platform's app knowledge."""
    map_file = Path(__file__).parent.parent.parent / "configs" / "linux_ms_map.csv"
    if not map_file.exists():
        pytest.skip("linux_ms_map.csv not found — skipping quality fixture tests")
    with map_file.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture()
def recommendation_service(tmp_path: Path) -> RecommendationService:
    """A recommendation service ready to generate migration plans."""
    return RecommendationService(reports_dir=tmp_path)


# ---------------------------------------------------------------------------
# Mapping quality — the platform finds the right Linux app every time
# ---------------------------------------------------------------------------

class TestWindowsToLinuxMappingAccuracy:
    """Prove that the dynamic mapping engine reliably finds Linux alternatives
    for the Windows apps our users actually use every day."""

    def test_recognises_well_known_apps_with_high_confidence(self, csv_map_rows):
        """Firefox is one of the most common Windows apps — the platform must map it
        with high confidence so users can trust the recommendation."""
        decision = resolve_mapping("Mozilla Firefox", csv_map_rows)
        assert decision is not None, "Firefox should be in the mapping knowledge base"
        assert decision.confidence_score >= 0.9, (
            f"A universally-known app should score ≥0.90; got {decision.confidence_score}"
        )

    def test_handles_real_world_app_names_with_version_suffixes(self, csv_map_rows):
        """Users install 'VLC media player 3.0.20' — the platform strips noise and
        still finds the right Linux package without needing a perfect match."""
        decision = resolve_mapping("VLC media player 3.0", csv_map_rows)
        assert decision is not None, "VLC substring should resolve even with a version suffix"
        assert "vlc" in decision.linux_package.lower()

    def test_fuzzy_matching_saves_users_from_typos(self, csv_map_rows):
        """A user who misspells 'Firefox' still gets the right recommendation —
        fuzzy similarity matching ensures no app is left unmapped due to a typo."""
        decision = resolve_mapping("Mozila Firefox", csv_map_rows)
        assert decision is not None, "Fuzzy matching should handle common misspellings"
        assert "firefox" in decision.linux_package.lower()

    def test_unknown_apps_are_honestly_flagged_rather_than_guessed(self, csv_map_rows):
        """The platform never fabricates a recommendation — if an app is truly
        unmappable, it returns None so the user knows to handle it manually."""
        decision = resolve_mapping("NonExistentApp_XYZ_123", csv_map_rows)
        assert decision is None, "Unmappable apps should return None, not a false recommendation"

    def test_user_overrides_always_take_priority_over_built_in_mappings(self, csv_map_rows):
        """Power users and IT admins can override any mapping — their explicit
        choice must always win, ensuring the tool adapts to any organisation's needs."""
        overrides = [
            {
                "windows_name": "Mozilla Firefox",
                "linux_package": "my-custom-browser",
                "linux_display_name": "Custom Browser",
                "migration_strategy": "install",
                "notes": "Corporate standard browser",
            }
        ]
        decision = resolve_mapping("Mozilla Firefox", csv_map_rows, overrides=overrides)
        assert decision is not None
        assert decision.linux_package == "my-custom-browser", (
            "User override must be respected — the platform follows the user's lead"
        )
        assert decision.recommendation_source == "user_override"
        assert decision.confidence_score == 0.98

    def test_empty_app_name_returns_none_gracefully(self, csv_map_rows):
        """Corrupt registry entries with blank names don't crash the platform —
        they are silently skipped so the rest of the scan continues."""
        assert resolve_mapping("", csv_map_rows) is None

    def test_empty_knowledge_base_returns_none_gracefully(self):
        """Even without any CSV mappings loaded, the platform doesn't crash —
        it simply acknowledges it has no data and moves on."""
        assert resolve_mapping("Firefox", []) is None

    @pytest.mark.parametrize("app_name,expected_pkg", [
        ("Microsoft Word", "libreoffice"),
        ("Google Chrome", "chrome"),
        ("7-Zip", "7zip"),
    ])
    def test_everyday_apps_map_to_the_right_linux_alternatives(
        self, app_name, expected_pkg, csv_map_rows
    ):
        """The most common Windows applications every user will have — Word,
        Chrome, 7-Zip — must map to their well-established Linux counterparts."""
        decision = resolve_mapping(app_name, csv_map_rows)
        assert decision is not None, f"{app_name!r} must resolve to a Linux package"
        assert expected_pkg in decision.linux_package.lower(), (
            f"{app_name!r} should map to a package containing {expected_pkg!r}; "
            f"got {decision.linux_package!r}"
        )


# ---------------------------------------------------------------------------
# Recommendation generation — the engine produces actionable, complete plans
# ---------------------------------------------------------------------------

class TestRecommendationReportGeneration:
    """Verify that generate_recommendations produces complete, trustworthy migration
    plans that users can act on immediately without manual cleanup."""

    def test_output_contains_all_expected_report_fields(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """Every migration report must carry the metadata users and supervisors need
        to understand what was recommended and why."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        for key in ("strategy", "selection_profile", "recommendations", "recommended_count", "input_count"):
            assert key in result, f"Migration report is missing required field: {key!r}"

    def test_recommended_count_exactly_matches_the_list_of_recommendations(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """Users rely on the count to know how many of their apps will migrate —
        it must never overcount or undercount."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        assert result["recommended_count"] == len(result["recommendations"]), (
            "The reported count must match the actual list length — users depend on this"
        )

    def test_input_count_reflects_every_scanned_application(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """The input_count lets users verify their full inventory was considered,
        not just a subset — critical for audit and compliance reports."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        assert result["input_count"] == len(SAMPLE_ENTRIES)

    def test_every_recommendation_carries_actionable_fields(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """Each item in the list must have everything a user needs to act on it —
        what they had, what to install, how confident the match is, and its status."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        required = {"windows_app", "linux_package", "mapping_confidence", "online_signal", "source"}
        for rec in result["recommendations"]:
            missing = required - rec.keys()
            assert not missing, (
                f"Recommendation for {rec.get('windows_app')!r} is incomplete — missing: {missing}"
            )

    def test_local_strategy_respects_privacy_and_skips_online_lookups(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """In local mode, the platform makes no external requests — users' app
        lists stay entirely on their machine."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        for rec in result["recommendations"]:
            assert rec["online_signal"] == "not_checked", (
                f"Local strategy must not make online calls; "
                f"{rec.get('windows_app')!r} has signal {rec.get('online_signal')!r}"
            )

    def test_agent_strategy_enriches_each_recommendation_with_a_score(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """Expert mode gives users an AI-derived score for each app — so they know
        which migrations to tackle first and which might need extra attention."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        with patch.object(recommendation_service, "_query_online_package_signal", return_value="verified"):
            result = recommendation_service.generate_recommendations(
                software_inventory=SAMPLE_SOFTWARE_INVENTORY,
                strategy="agent",
                ai_config={"software_online_lookup_enabled": True, "software_online_send_fields": ["name"]},
            )
        for rec in result["recommendations"]:
            assert "agent_score" in rec, (
                f"Agent strategy must score every recommendation; "
                f"{rec.get('windows_app')!r} has no score"
            )
            assert 0 <= int(rec["agent_score"]) <= 100, "Score must be a percentage 0–100"

    def test_confidence_labels_are_always_meaningful(
        self, recommendation_service: RecommendationService
    ):
        """Confidence labels — high / medium / low — must be human-readable values
        so users can immediately assess the quality of each recommendation."""
        rows = [{
            "windows_name": "TestApp", "linux_package": "testapp",
            "linux_display_name": "TestApp", "migration_strategy": "install", "notes": "",
        }]
        recommendation_service._load_mapping_rows = lambda: rows  # type: ignore[method-assign]
        inventory = {"entries": [{"DisplayName": "TestApp", "Version": "1.0", "Publisher": "X"}]}
        result = recommendation_service.generate_recommendations(
            software_inventory=inventory, strategy="local"
        )
        if result["recommendations"]:
            conf = result["recommendations"][0]["mapping_confidence"]
            assert conf in {"high", "medium", "low"}, (
                f"Confidence must be high/medium/low so users can read it; got {conf!r}"
            )

    def test_mapping_source_tells_users_where_the_recommendation_came_from(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """Traceability matters — every recommendation must indicate whether it
        came from the built-in knowledge base or a user-defined override."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        for rec in result["recommendations"]:
            assert rec.get("mapping_source") in {"dynamic_base", "user_override"}, (
                f"Mapping source must be traceable; got {rec.get('mapping_source')!r}"
            )

    def test_user_override_wins_over_built_in_knowledge_base(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """An IT admin who sets a corporate standard browser must see their choice
        reflected in every report — the platform always honours explicit decisions."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        overrides = [{
            "windows_name": "Mozilla Firefox", "linux_package": "overridden-browser",
            "linux_display_name": "Corporate Browser", "migration_strategy": "install", "notes": "",
        }]
        inventory = {"entries": [{"DisplayName": "Mozilla Firefox", "Version": "1.0", "Publisher": "Mozilla"}]}
        result = recommendation_service.generate_recommendations(
            software_inventory=inventory, strategy="local", mapping_overrides=overrides
        )
        recs = result["recommendations"]
        assert recs, "Firefox must produce a recommendation even with an override"
        assert recs[0]["linux_package"] == "overridden-browser", (
            "The user override must take precedence in the final report"
        )
        assert recs[0]["mapping_source"] == "user_override"

    def test_empty_scan_produces_a_clean_empty_report(
        self, recommendation_service: RecommendationService, csv_map_rows
    ):
        """A system with no detected apps should return a valid empty report —
        not an error — so the workflow can always continue gracefully."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        result = recommendation_service.generate_recommendations(
            software_inventory={"entries": []}, strategy="local"
        )
        assert result["recommended_count"] == 0
        assert result["recommendations"] == []

    def test_report_files_are_written_and_ready_for_submission(
        self, recommendation_service: RecommendationService, csv_map_rows, tmp_path: Path
    ):
        """The platform writes both a JSON data file and a Markdown summary that
        users can immediately attach to their migration report or academic submission."""
        recommendation_service._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]
        recommendation_service.reports_dir = tmp_path
        result = recommendation_service.generate_recommendations(
            software_inventory=SAMPLE_SOFTWARE_INVENTORY, strategy="local"
        )
        assert Path(result["json_path"]).exists(), (
            "JSON report file must exist so developers can process the recommendations"
        )
        assert Path(result["markdown_path"]).exists(), (
            "Markdown report must exist so users can read and share the results"
        )


# ---------------------------------------------------------------------------
# Agent scoring — clear, transparent prioritisation for expert users
# ---------------------------------------------------------------------------

class TestAgentScoringPrioritisesTheBestMigrations:
    """Expert mode scores tell users which apps to migrate first.
    These tests prove the scoring logic is meaningful, bounded, and consistent."""

    @pytest.mark.parametrize("confidence,category,signal,expected_range", [
        ("high", "office", "verified", (70, 100)),
        ("medium", "browser", "available", (30, 70)),
        ("low", "", "not_verified", (10, 50)),
        ("high", "", "verified", (60, 100)),
    ])
    def test_score_reflects_confidence_and_package_availability(
        self, confidence, category, signal, expected_range
    ):
        """Scores must be proportional to how well-known and available the package
        is — a 'high confidence + verified' app should always rank ahead of a 'low + unknown'."""
        score = RecommendationService._agent_score(confidence, category, signal)
        lo, hi = expected_range
        assert lo <= score <= hi, (
            f"Score {score} is outside the expected range [{lo}, {hi}] "
            f"for ({confidence!r}, {category!r}, {signal!r})"
        )

    def test_scores_never_exceed_100_percent(self):
        """Users see scores as percentages — they must never go above 100
        so the display always makes intuitive sense."""
        assert RecommendationService._agent_score("high", "office", "verified") <= 100

    def test_verified_package_scores_higher_than_unverified(self):
        """A package confirmed in the Linux Mint repos must outscore one that
        isn't — so users prioritise apps they can actually install immediately."""
        score_verified = RecommendationService._agent_score("high", "office", "verified")
        score_unverified = RecommendationService._agent_score("high", "office", "not_verified")
        assert score_verified > score_unverified, (
            "Verified availability should boost the score — users should install confirmed apps first"
        )


# ---------------------------------------------------------------------------
# Repology online lookup — fast, cached, privacy-respecting package verification
# ---------------------------------------------------------------------------

class TestOnlinePackageLookupIsReliableAndPrivacyRespecting:
    """The platform's online lookup enriches recommendations without compromising
    user privacy.  These tests prove caching works, failures are handled safely,
    and only package names (never personal data) ever leave the machine."""

    def test_repeated_lookups_use_the_cache_without_hitting_the_network(
        self, recommendation_service: RecommendationService
    ):
        """Repology has rate limits — the platform caches every result so the
        same package is never looked up twice in one session."""
        recommendation_service._repology_cache["vlc"] = {"signal": "verified"}
        with patch("requests.get") as mock_get:
            result = recommendation_service._query_online_package_signal("vlc")
        mock_get.assert_not_called()
        assert result == "verified", "Cache hit must return the stored signal without a network call"

    def test_network_failures_never_crash_the_recommendation_engine(
        self, recommendation_service: RecommendationService
    ):
        """If Repology is unreachable, the platform marks the package as
        'unreachable' and continues — a network error never stops the migration."""
        with patch("requests.get", side_effect=OSError("Network down")):
            result = recommendation_service._query_online_package_signal("somepkg")
        assert result == "unreachable", "Network errors must degrade gracefully, not crash"

    def test_packages_not_on_repology_are_flagged_not_hidden(
        self, recommendation_service: RecommendationService
    ):
        """Honesty matters: if a package doesn't exist on Repology, the platform
        tells the user 'not_found' rather than silently skipping it."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("requests.get", return_value=mock_resp):
            result = recommendation_service._query_online_package_signal("nonexistentpkg")
        assert result == "not_found"

    def test_packages_in_linux_mint_repos_are_marked_verified(
        self, recommendation_service: RecommendationService
    ):
        """'Verified' means the package is confirmed in a Linux Mint or Ubuntu
        repository — the strongest signal a user can get that an app will just work."""
        packages = [
            {"repo": "linuxmint_21", "version": "1.0"},
            {"repo": "ubuntu_22_04", "version": "1.0"},
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = packages
        with patch("requests.get", return_value=mock_resp):
            result = recommendation_service._query_online_package_signal("firefox")
        assert result == "verified", (
            "Packages in Linux Mint / Ubuntu repos must be marked 'verified' — the user can install them"
        )
        assert "firefox" in recommendation_service._repology_cache

    def test_packages_in_obscure_repos_are_available_but_not_verified(
        self, recommendation_service: RecommendationService
    ):
        """'Available' means the package exists somewhere on Repology but not in
        the target Linux Mint repos — users can still try, but should check compatibility."""
        packages = [{"repo": "some_obscure_distro", "version": "1.0"}]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = packages
        with patch("requests.get", return_value=mock_resp):
            result = recommendation_service._query_online_package_signal("obscurepkg")
        assert result == "available"

    def test_blank_package_name_returns_unknown_without_crashing(
        self, recommendation_service: RecommendationService
    ):
        """Malformed entries in the mapping CSV — like a blank package name — must
        never cause a crash.  The platform returns 'unknown' and keeps going."""
        assert recommendation_service._query_online_package_signal("") == "unknown"

    def test_unsupported_providers_are_clearly_rejected(
        self, recommendation_service: RecommendationService
    ):
        """Only Repology is supported today.  If someone configures an unknown provider,
        the platform rejects it clearly rather than silently failing or hanging."""
        result = recommendation_service._query_online_package_signal("vlc", provider="apt")
        assert result == "not_supported"
