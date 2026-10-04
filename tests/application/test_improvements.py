from copy import deepcopy
import json

import pytest

from ww3.core.ai import prepare_ai_orders, prepare_computer_orders
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import new_game, resolve_round
from ww3.evaluation import POLICIES, aggregate, replay_campaign, run_campaign, scripted_orders
from ww3.core.forecast import forecast_round
from ww3.persistence import dumps, loads
from ww3.application.planning import DraftHistory, compare_draft
from ww3.core.rules import Rules


def test_remembered_draft_is_independent_restorable_and_undoable():
    game = new_game()
    history = DraftHistory(game)
    game.orders["EU"].investments = {"factory": 10}
    history.record(game, "EU")
    history.remember(game, "EU")
    game.orders["EU"].investments.clear()
    game.orders["EU"].tax_rate = .5
    history.record(game, "EU")
    assert history.remembered["EU"].investments == {"factory": 10}
    assert history.restore_remembered(game, "EU")
    assert game.orders["EU"].investments == {"factory": 10}
    assert history.restore(game, "EU")
    assert game.orders["EU"].tax_rate == .5
    game.submitted = ["EU"]
    assert not history.restore_remembered(game, "EU")


@pytest.mark.parametrize("mode", ["solo", "hotseat", "sandbox"])
def test_comparison_uses_actual_current_rival_drafts_and_never_changes_state(mode):
    game = new_game(mode=mode)
    remembered = deepcopy(game.orders["EU"])
    game.orders["EU"].investments = {"factory": 10}
    game.orders["US"].deployments = dict(zip(FRONTS, [10, 100, 150, 0]))
    before = deepcopy(game)
    compared = compare_draft(game, "EU", remembered)
    assert game == before
    assert compared["current"]["forecast"] == forecast_round(game)
    alternate = deepcopy(game)
    alternate.orders["EU"] = remembered
    assert compared["remembered"]["forecast"] == forecast_round(alternate)
    resolved = resolve_round(prepare_ai_orders(alternate))
    for row in compared["remembered"]["forecast"]["factions"]["EU"]["resources"]:
        actual = resolved.debt("EU") if row["key"] == "debt" else getattr(resolved.nations["EU"], row["key"])
        assert row["expected"] == pytest.approx(actual)


def test_invalid_alternative_does_not_suppress_the_valid_draft():
    game = new_game()
    remembered = deepcopy(game.orders["EU"])
    remembered.investments = {"factory": 10, "research": 10}
    comparison = compare_draft(game, "EU", remembered)
    assert comparison["current"]["forecast"]
    assert comparison["remembered"]["forecast"] is None
    assert "productivity" in comparison["remembered"]["error"]


def test_explicit_computer_factions_preserve_normal_solo_behavior():
    game = new_game()
    assert prepare_ai_orders(game) == prepare_computer_orders(game, ["Russia", "China", "US"])
    assert prepare_computer_orders(game, []) == game
    with pytest.raises(ValueError):
        prepare_computer_orders(game, ["unknown"])


@pytest.mark.parametrize("faction", FACTIONS)
@pytest.mark.parametrize("policy", POLICIES)
def test_diagnostic_policies_use_valid_real_orders_and_stock_budgets(faction, policy):
    game = new_game(player=faction)
    original = dumps(game)
    for _ in range(3):
        prepared = scripted_orders(game, policy)
        assert dumps(game) == original
        game = resolve_round(prepared)
        assert loads(dumps(game)) == game
        original = dumps(game)


def test_recorded_campaign_replays_and_truncated_or_edited_transcripts_fail(tmp_path):
    path = tmp_path / "campaign"
    summary, records = run_campaign("China", "research", 23, 4, directory=path)
    assert replay_campaign(path)["verified_years"] == 4
    assert summary["stop_reason"] == "observation_limit"
    assert len(records) == 4
    transcript = path / "orders.jsonl"
    original = transcript.read_text()
    transcript.write_text("\n".join(original.splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="incomplete"):
        replay_campaign(path)
    changed = json.loads(original.splitlines()[0])
    changed["orders"]["China"]["tax_rate"] = .5
    transcript.write_text(json.dumps(changed) + "\n" + "\n".join(original.splitlines()[1:]) + "\n")
    with pytest.raises(ValueError, match="diverged"):
        replay_campaign(path)


def test_campaign_outcomes_reproducible_and_limit_is_not_victory(tmp_path):
    a, records_a = run_campaign("US", "military", 17, 3)
    b, records_b = run_campaign("US", "military", 17, 3)
    assert (a, records_a) == (b, records_b)
    assert a["first_victory_round"] is None and not a["winners"]
    assert aggregate([a, b])["unresolved"] == 2
    initial = new_game(rules=Rules(victory_mode="influence", victory_target=1))
    victory, records = run_campaign(policy="current", turns=10, initial=initial, directory=tmp_path / "win")
    assert victory["stop_reason"] == "victory" and victory["years_resolved"] == 1
    assert replay_campaign(tmp_path / "win")["winners"] == victory["winners"]


def test_evaluation_never_overwrites_existing_artifacts(tmp_path):
    with pytest.raises(FileExistsError):
        run_campaign(directory=tmp_path)
