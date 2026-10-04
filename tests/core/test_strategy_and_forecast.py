from copy import deepcopy
import json
from pathlib import Path

import pytest

from ww3.core.ai import prepare_ai_orders
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import InvalidOrder, domestic_interest, investment_cost, new_game, resolve_round
from ww3.core.forecast import forecast_round
from ww3.core.models import pair
from ww3.persistence import dumps, loads
from ww3.core.rules import Rules
from ww3.core.strategy import dominance, dominance_bonus, objective_progress


def empty_board(**kwargs):
    game = new_game(**kwargs)
    for f in FACTIONS:
        game.nations[f].deployments = dict.fromkeys(FRONTS, 0.0)
        game.orders[f].deployments = dict.fromkeys(FRONTS, 0.0)
    for front in game.fronts.values():
        front.influence = dict.fromkeys(FACTIONS, 0.0)
        front.status = "Uncommitted"
    return game


def eu_winning_position(**kwargs):
    game = empty_board(mode="sandbox", **kwargs)
    game.nations["EU"].deployments[FRONTS[0]] = 60
    game.orders["EU"].deployments[FRONTS[0]] = 60
    return game


def test_opening_objectives_and_deployments_match_design():
    game = new_game()
    expected_reserves = {"EU": 40, "US": 140, "China": 50, "Russia": 60}
    for f in FACTIONS:
        assert game.nations[f].military - sum(game.nations[f].deployments.values()) == expected_reserves[f]
        assert not all(x["met"] for x in objective_progress(game, f))
        assert game.objective_streaks[f] == 0
    assert game.nations["EU"].deployments[FRONTS[0]] == 60
    assert game.nations["Russia"].deployments[FRONTS[0]] == 80
    assert dominance(game, FRONTS[0])["EU"] == pytest.approx(60 / 140)
    assert [x["met"] for x in objective_progress(game, "EU")] == [False, False, True]
    assert game.fronts[FRONTS[0]].influence["Russia"] == 45


def test_summary_values_fill_gaps_without_overriding_original_values():
    game = new_game()
    assert [n.currency for n in game.nations.values()] == [60, 50, 40, 10]
    assert [n.productivity for n in game.nations.values()] == [10, 12, 15, 8]
    assert [n.content for n in game.nations.values()] == [60, 75, 80, 74]
    assert [n.energy for n in game.nations.values()] == [10, 20, 15, 30]
    assert [n.minerals for n in game.nations.values()] == [5, 5, 20, 10]
    assert [n.innovation for n in game.nations.values()] == [5, 8, 6, 2]
    assert all(n.compute == 0 for n in game.nations.values())
    assert game.nations["China"].tax_rate == .204
    assert domestic_interest(game, "EU") == pytest.approx(.09)


@pytest.mark.parametrize("own,other,bonus", [(0, 0, 0), (24, 76, 0), (25, 75, .05), (50, 50, .10), (75, 25, .15), (100, 0, .15)])
def test_dominance_revenue_boundaries(own, other, bonus):
    game = empty_board()
    game.nations["EU"].deployments[FRONTS[0]] = own
    game.nations["China"].deployments[FRONTS[0]] = other
    assert dominance_bonus(game, "EU") == bonus


def test_allies_do_not_double_count_tax_dominance():
    game = empty_board()
    game.alliances = [pair("EU", "US")]
    game.nations["EU"].deployments[FRONTS[0]] = 25
    game.nations["US"].deployments[FRONTS[0]] = 75
    assert dominance_bonus(game, "EU") == .05
    assert dominance_bonus(game, "US") == .15


def test_contested_front_gives_tax_bonus_but_no_influence():
    game = empty_board()
    game.orders["EU"].deployments[FRONTS[0]] = 75
    game.orders["China"].deployments[FRONTS[0]] = 25
    result = resolve_round(game)
    assert result.nations["EU"].last_ledger["dominance_income"] == pytest.approx(20 * .4 * .15)
    assert result.fronts[FRONTS[0]].influence["EU"] == 0


def test_eu_allied_security_needs_eu_presence_and_excludes_russia():
    game = empty_board()
    game.alliances = [pair("EU", "US")]
    game.nations["US"].deployments[FRONTS[0]] = 100
    assert not objective_progress(game, "EU")[0]["met"]
    game.nations["EU"].deployments[FRONTS[0]] = 20
    assert objective_progress(game, "EU")[0]["met"]
    game.alliances.append(pair("US", "Russia"))
    game.nations["Russia"].deployments[FRONTS[0]] = 10
    assert not objective_progress(game, "EU")[0]["met"]


def test_eu_arctic_threshold_includes_allies_and_empty_is_neutral():
    game = eu_winning_position()
    game.alliances = [pair("EU", "US")]
    for f, power in zip(FACTIONS, (20, 40, 20, 20)):
        game.nations[f].deployments[FRONTS[2]] = power
    assert objective_progress(game, "EU")[2]["met"]
    game.nations["US"].deployments[FRONTS[2]] = 41
    assert not objective_progress(game, "EU")[2]["met"]
    for f in FACTIONS:
        game.nations[f].deployments[FRONTS[2]] = 0
    assert objective_progress(game, "EU")[2]["met"]


def test_russian_influence_threshold_is_recoverable():
    game = eu_winning_position()
    game.fronts[FRONTS[0]].influence = {"EU": 85.0, "US": 0.0, "China": 0.0, "Russia": 15.0}
    assert not objective_progress(game, "EU")[1]["met"]
    result = resolve_round(game)
    assert result.fronts[FRONTS[0]].influence["Russia"] == 5
    assert result.objective_streaks["EU"] == 1


def test_victory_requires_three_completed_rounds_and_survives_save():
    game = eu_winning_position()
    assert not game.winners
    for year in (1, 2, 3):
        game = resolve_round(game)
        assert game.objective_streaks["EU"] == year
        assert game.winners == (["EU"] if year == 3 else [])
        game = loads(dumps(game))
    assert resolve_round(game).winners == ["EU"]


def test_failed_objective_resets_the_entire_streak():
    game = resolve_round(resolve_round(eu_winning_position()))
    assert game.objective_streaks["EU"] == 2
    game.orders["US"].deployments[FRONTS[2]] = 10
    game = resolve_round(game)
    assert game.objective_streaks["EU"] == 0 and not game.winners
    game.orders["US"].deployments[FRONTS[2]] = 0
    for expected in (1, 2, 3):
        game = resolve_round(game)
        assert game.objective_streaks["EU"] == expected
    assert game.winners == ["EU"]


def test_open_mode_tracks_objectives_without_declaring_victory():
    game = eu_winning_position(rules=Rules(victory_mode="open"))
    for _ in range(5):
        game = resolve_round(game)
    assert not game.winners
    assert game.objective_streaks["EU"] == 3


def test_equal_influence_leaders_are_co_winners():
    game = empty_board(rules=Rules(victory_mode="influence", victory_target=150))
    for front in game.fronts.values():
        front.influence = {"EU": 40.0, "US": 40.0, "China": 10.0, "Russia": 10.0}
    assert resolve_round(game).winners == ["EU", "US"]


def test_chinese_pacific_threshold_is_strict():
    game = empty_board()
    game.nations["China"].deployments[FRONTS[1]] = 80
    game.nations["US"].deployments[FRONTS[1]] = 20
    assert not objective_progress(game, "China")[0]["met"]
    game.nations["China"].deployments[FRONTS[1]] = 81
    assert objective_progress(game, "China")[0]["met"]


def test_reserve_recovery_never_increases_capacity_or_deployed_forces():
    game = empty_board()
    n = game.nations["EU"]
    n.military = 100
    n.buildings["drone"] = n.buildings["cyber"] = 0
    result = resolve_round(game)
    assert result.nations["EU"].military == pytest.approx(101.2)
    assert result.nations["EU"].military_capacity == 120
    assert sum(result.nations["EU"].deployments.values()) == 0
    game.orders["EU"].deployments[FRONTS[0]] = 100
    assert resolve_round(game).nations["EU"].military == 100


def test_data_center_innovation_is_one_time():
    game = empty_board()
    game.nations["EU"].buildings["research"] = 0
    game.orders["EU"].investments = {"datacenter": 7.5}
    first = resolve_round(game)
    assert first.nations["EU"].innovation == pytest.approx(5 + 1.1 * 1.1)
    assert resolve_round(first).nations["EU"].innovation == first.nations["EU"].innovation


@pytest.mark.parametrize("mode", ["solo", "hotseat", "sandbox"])
def test_forecast_matches_actual_resolution_without_mutation(mode):
    game = new_game(mode=mode)
    game.orders["EU"].investments = {"factory": 10}
    before = dumps(game)
    forecast = forecast_round(game)
    assert dumps(game) == before
    resolved = resolve_round(prepare_ai_orders(game))
    for f in FACTIONS:
        for row in forecast["factions"][f]["resources"]:
            actual = resolved.debt(f) if row["key"] == "debt" else getattr(resolved.nations[f], row["key"])
            assert row["expected"] == pytest.approx(actual)
            assert row["change"] == pytest.approx(row["expected"] - row["current"])
            assert row["after_orders"] + row["system_change"] == pytest.approx(row["expected"])
    rows = {r["key"]: r for r in forecast["factions"]["EU"]["resources"]}
    assert rows["productivity"]["after_orders"] == 0
    assert rows["productivity"]["expected"] == 15
    assert rows["currency"]["after_orders"] == pytest.approx(60 - investment_cost(game, "EU", "factory")["currency"])


def test_forecast_reacts_to_tax_and_construction_choices():
    game = new_game()
    baseline = forecast_round(game)
    game.orders["EU"].tax_rate = .5
    higher_tax = forecast_round(game)
    before = baseline["factions"]["EU"]["resources"][0]["expected"]
    after = higher_tax["factions"]["EU"]["resources"][0]["expected"]
    assert after > before
    assert higher_tax["factions"]["EU"]["ledger"]["taxes"] == 10
    game.orders["EU"].investments = {"factory": 10}
    built = forecast_round(game)
    assert next(r for r in built["factions"]["EU"]["resources"] if r["key"] == "productivity")["expected"] == 15


def test_invalid_forecast_does_not_advance_or_change_world():
    game = new_game()
    game.orders["EU"].investments = {"factory": 11}
    before = deepcopy(game)
    with pytest.raises(InvalidOrder):
        forecast_round(game)
    assert game == before


def test_actual_prototype_save_migrates_and_remains_playable():
    payload = (Path(__file__).resolve().parents[1] / "fixtures" / "prototype-v1.json").read_text()
    original = json.loads(payload)
    game = loads(payload)
    assert game.round == original["round"]
    for f in FACTIONS:
        assert game.nations[f].currency == original["nations"][f]["currency"]
        assert game.nations[f].deployments == original["nations"][f]["deployments"]
    assert game.objective_streaks == dict.fromkeys(FACTIONS, 0)
    assert loads(dumps(game)) == game
    assert resolve_round(prepare_ai_orders(game)).round == game.round + 1
