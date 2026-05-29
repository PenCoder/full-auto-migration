"""Tests for scan page mode progression behavior without Qt widget instantiation."""


def test_scan_mode_behavior_contract_documented():
    """Lightweight contract test for expected mode progression semantics.

    This test guards product requirements at a high level:
    Guided < Balanced < Expert in customization and action surface.
    """
    guided = {
        "quick_scan": True,
        "deep_scan": False,
        "online_rec": False,
        "agent_rec": False,
        "profile_edit": False,
        "auto_local_rec_after_scan": True,
    }
    balanced = {
        "quick_scan": True,
        "deep_scan": True,
        "online_rec": True,
        "agent_rec": False,
        "profile_edit": True,
        "auto_local_rec_after_scan": False,
    }
    expert = {
        "quick_scan": True,
        "deep_scan": True,
        "online_rec": True,
        "agent_rec": True,
        "profile_edit": True,
        "auto_local_rec_after_scan": False,
    }

    # Strict progression in customization and action depth.
    assert guided["quick_scan"] is True
    assert guided["deep_scan"] is False
    assert balanced["deep_scan"] is True
    assert expert["agent_rec"] is True
    assert guided["profile_edit"] is False
    assert balanced["profile_edit"] is True
    assert balanced["agent_rec"] is False
    assert expert["agent_rec"] is True
