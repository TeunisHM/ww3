import json
from pathlib import Path

import pytest

from ww3.application.session import GameSession, RevisionConflict, SessionError
from ww3.core.ai import prepare_ai_orders
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import InvalidOrder, resolve_round
from ww3.persistence import loads


@pytest.mark.parametrize("mode", ["solo", "hotseat", "sandbox"])
def test_both_client_workflows_use_the_same_forecast_and_resolution(mode):
    session = GameSession.new(mode)
    assert session.edit_order("EU", {"investments": {"factory": 5}, "tax_rate": .35})
    opening = session.snapshot()
    forecast = session.forecast()
    assert session.snapshot() == opening
    expected = resolve_round(prepare_ai_orders(opening))
    if mode == "hotseat":
        for faction in FACTIONS[:-1]:
            result = session.commit(faction)
            assert not result.resolved
            assert session.snapshot().round == opening.round
        result = session.commit(FACTIONS[-1])
    else:
        result = session.commit("EU")
    assert result.resolved
    assert session.snapshot() == expected
    assert not session.draft_history.undo["EU"]
    for faction, data in forecast["factions"].items():
        for row in data["resources"]:
            actual = expected.debt(faction) if row["key"] == "debt" else getattr(expected.nations[faction], row["key"])
            assert row["expected"] == pytest.approx(actual)


def test_invalid_drafts_survive_export_but_cannot_advance_or_destroy_undo():
    session = GameSession.new()
    session.edit_order("EU", {"investments": {"factory": 10, "research": 10}})
    before, revision = session.export(), session.revision
    assert loads(before, allow_invalid_drafts=True).orders["EU"].investments["research"] == 10
    with pytest.raises(InvalidOrder):
        session.commit("EU")
    assert session.export() == before and session.revision == revision
    assert session.undo("EU")
    assert session.forecast()


def test_failed_final_hotseat_commit_preserves_every_submission_and_world():
    session = GameSession.new("hotseat")
    for faction in FACTIONS[:-1]:
        session.commit(faction)
    last = FACTIONS[-1]
    session.edit_order(last, {"deployments": dict.fromkeys(FRONTS, 10000)})
    before, revision = session.export(), session.revision
    with pytest.raises(InvalidOrder):
        session.commit(last)
    assert session.export() == before and session.revision == revision
    assert session.snapshot().submitted == list(FACTIONS[:-1])
    session.reset_draft(last)
    assert session.commit(last).resolved


def test_committed_drafts_are_locked_and_reopen_is_explicit():
    session = GameSession.new("hotseat")
    session.edit_order("EU", {"tax_rate": .35})
    session.commit("EU")
    for action in (
        lambda: session.edit_order("EU", {"tax_rate": .4}),
        lambda: session.undo("EU"), lambda: session.reset_draft("EU"),
        lambda: session.remember("EU"), lambda: session.restore_remembered("EU"),
        lambda: session.commit("EU"),
    ):
        with pytest.raises(SessionError, match="committed"):
            action()
    session.reopen("EU")
    assert session.undo("EU")


@pytest.mark.parametrize("changes", [
    {"tax_rate": float("nan")}, {"tax_rate": True}, {"deployments": []},
    {"investments": {"invented": 1}}, {"government": "unknown"}, {"extra": 5},
])
def test_malformed_edits_are_atomic(changes):
    session = GameSession.new()
    before = session.export()
    with pytest.raises(ValueError):
        session.edit_order("EU", changes)
    assert session.export() == before and session.revision == 0


def test_snapshots_orders_and_alternatives_do_not_expose_mutable_session_state():
    session = GameSession.new()
    game = session.snapshot()
    game.orders["EU"].tax_rate = .45
    assert session.snapshot().orders["EU"].tax_rate != .45
    session.replace_order("EU", game.orders["EU"])
    game.orders["EU"].tax_rate = .6
    session.remember("EU")
    session.edit_order("EU", {"tax_rate": .3})
    before = session.export()
    assert session.compare("EU")["remembered"]["forecast"]
    assert session.export() == before
    assert session.restore_remembered("EU")
    assert session.snapshot().orders["EU"].tax_rate == .45
    assert session.undo("EU")
    assert session.snapshot().orders["EU"].tax_rate == .3


def test_solo_client_cannot_edit_or_commit_a_computer_opponent():
    session = GameSession.new()
    with pytest.raises(SessionError, match="Computer"):
        session.edit_order("US", {"tax_rate": .1})
    with pytest.raises(SessionError, match="Computer"):
        session.commit("US")


def test_load_preserves_drafts_and_rules_and_invalid_load_is_atomic():
    session = GameSession.new()
    session.edit_order("EU", {"tax_rate": .3})
    old = session.export()
    session.commit("EU")
    revision = session.revision
    session.load(old)
    assert session.revision == revision + 1
    assert session.export() == old
    assert not session.draft_history.undo["EU"]
    with pytest.raises(ValueError):
        session.load('{"schema_version":999}')
    assert session.export() == old
    with pytest.raises(RevisionConflict):
        session.check_revision(revision)
    session.check_revision(session.revision)


def test_frozen_pre_migration_campaign_matches_session():
    fixture = json.loads((Path(__file__).parents[1] / "fixtures" / "migration-baseline.json").read_text())
    session = GameSession(loads(json.dumps(fixture["initial"])))
    for step in fixture["steps"]:
        session.edit_order("EU", step["changes"])
        assert session.forecast() == step["forecast"]
        session.commit("EU")
        assert session.snapshot().to_dict() == step["result"]
