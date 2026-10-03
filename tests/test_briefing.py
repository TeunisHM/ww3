from copy import deepcopy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ww3.briefing import objective_briefing, objective_gap, resource_alerts, victory_watch
from ww3.catalog import FACTIONS, FRONTS
from ww3.engine import new_game, resolve_round
from ww3.forecast import forecast_round
from ww3.persistence import dumps
from ww3.rules import Rules
from ww3.strategy import EPS, objective_progress


APP = str(Path(__file__).parents[1] / "app.py")


def empty_world(rules=None):
    game = new_game(mode="sandbox", rules=rules or Rules())
    for faction in FACTIONS:
        game.nations[faction].deployments = dict.fromkeys(FRONTS, 0.0)
        game.orders[faction].deployments = dict.fromkeys(FRONTS, 0.0)
    for front in game.fronts.values():
        front.influence = dict.fromkeys(FACTIONS, 0.0)
    return game


def test_gaps_use_objective_rule_values_and_strict_targets():
    game = new_game()
    security, influence, _ = objective_progress(game, "EU")
    assert objective_gap(security) == "Increase by 17.1 percentage points to satisfy the condition."
    assert objective_gap(influence) == "Reduce by 35.0 influence to satisfy the condition."
    game.nations["China"].deployments[FRONTS[1]] = 80
    game.nations["US"].deployments[FRONTS[1]] = 20
    assert "equality does not satisfy" in objective_gap(objective_progress(game, "China")[0])
    assert "20.0 power" in objective_gap(objective_progress(game, "US")[0])
    game.nations["China"].deployments[FRONTS[3]] = .01
    game.nations["Russia"].deployments[FRONTS[3]] = 0
    assert "0.01 power" in objective_gap(objective_progress(game, "US")[0])


def test_briefing_uses_post_combat_and_identifies_the_influence_blocker():
    game = new_game(mode="sandbox")
    game.orders["EU"].deployments[FRONTS[0]] = 100
    game.orders["EU"].deployments[FRONTS[2]] = 20
    before = dumps(game)
    forecast = forecast_round(game)
    cards = objective_briefing(game, "EU", forecast)
    assert cards[0]["expected"] == objective_progress(resolve_round(game), "EU")[0]
    assert cards[0]["expected"]["value"] != pytest.approx(100 / 180)
    assert "Still contested after combat" in cards[1]["blocker"]
    assert "Russia" in cards[1]["blocker"]
    assert "No new influence" in cards[1]["blocker"]
    assert dumps(game) == before


def test_hold_reset_is_identified_before_resolution():
    game = empty_world()
    game.nations["EU"].deployments[FRONTS[0]] = 60
    game.orders["EU"].deployments[FRONTS[0]] = 60
    game.objective_streaks["EU"] = 2
    game.orders["US"].deployments[FRONTS[2]] = 10
    forecast = forecast_round(game)
    cards = objective_briefing(game, "EU", forecast)
    assert cards[2]["change"] == "At risk"
    row = next(item for item in victory_watch(game, forecast) if item["faction"] == "EU")
    assert row["current"] == 2 and row["expected"] == 0
    assert not row["wins_this_year"]


@pytest.mark.parametrize("mode,expected_winners", [("objectives", ["US"]), ("open", [])])
def test_imminent_winner_respects_victory_mode(mode, expected_winners):
    game = empty_world(Rules(victory_mode=mode, objective_hold_years=5))
    game.objective_streaks["US"] = 4
    game.orders["US"].deployments[FRONTS[2]] = 10
    forecast = forecast_round(game)
    assert [item["faction"] for item in victory_watch(game, forecast) if item["wins_this_year"]] == expected_winners
    assert resolve_round(game).winners == expected_winners


@pytest.mark.parametrize("difference,expected_winners", [(0, ["EU", "US"]), (EPS / 2, ["EU", "US"]), (5, ["EU"])])
def test_influence_watch_only_predicts_leaders_including_ties(difference, expected_winners):
    game = empty_world(Rules(victory_mode="influence", victory_target=160))
    for front in game.fronts.values():
        front.influence = dict(zip(FACTIONS, (40, 40, 10, 10)))
    game.fronts[FRONTS[0]].influence["US"] -= difference
    forecast = forecast_round(game)
    assert [item["faction"] for item in victory_watch(game, forecast) if item["wins_this_year"]] == expected_winners
    assert resolve_round(game).winners == expected_winners


def test_missing_forecast_never_claims_future_progress_or_victory():
    game = new_game()
    game.objective_streaks["US"] = game.rules.objective_hold_years
    cards = objective_briefing(game, "EU")
    assert all(item["expected"] is None and item["change"] == "Forecast unavailable" for item in cards)
    assert all(item["expected"] is None and not item["wins_this_year"] for item in victory_watch(game))
    assert resource_alerts(game, "EU", None) == []


def test_secured_victory_is_not_announced_as_a_new_forecast_win():
    game = empty_world()
    game.winners = ["US"]
    game.objective_streaks["US"] = game.rules.objective_hold_years
    game.orders["US"].deployments[FRONTS[2]] = 10
    rows = victory_watch(game, forecast_round(game))
    assert not any(item["wins_this_year"] for item in rows)
    assert next(item for item in rows if item["faction"] == "US")["secured"]


def test_resource_alerts_surface_shortage_and_borrowing_without_mutation():
    game = new_game()
    game.nations["EU"].domestic_debt = 10000
    game.nations["EU"].compute = 0
    game.nations["EU"].buildings["datacenter"] = 0
    forecast = forecast_round(game)
    original = deepcopy(forecast)
    alerts = resource_alerts(game, "EU", forecast)
    assert any("compute operation" in text for _, text in alerts)
    assert any("new domestic borrowing" in text and "operating deficit" in text for _, text in alerts)
    assert any("10.0 unallocated productivity" in text for _, text in alerts)
    assert forecast == original


def test_objective_navigation_preserves_draft_and_time():
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.button(key="quick_start").click().run()
    app.radio(key="page").set_value("Objectives").run()
    assert not app.exception
    assert any("Expected hold after combat" in item.value for item in app.markdown)
    assert any("Expected gap" in item.value for item in app.markdown)
    draft = deepcopy(app.session_state.game.orders["EU"])
    app.button(key="objective_front_EU_2").click().run()
    assert not app.exception
    assert app.radio(key="page").value == "Military fronts"
    assert app.selectbox(key="front_selector").value == FRONTS[2]
    assert app.session_state.game.round == 1
    assert app.session_state.game.orders["EU"] == draft


def test_invalid_draft_clears_objective_predictions_in_ui():
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.button(key="quick_start").click().run()
    app.radio(key="page").set_value("Economy & construction").run()
    prefix = f"{app.session_state.epoch}:1:EU:"
    app.number_input(key=prefix + "factory").set_value(10.0).run()
    app.number_input(key=prefix + "research").set_value(10.0).run()
    app.radio(key="page").set_value("Objectives").run()
    assert not app.exception
    assert app.button(key="end_year").disabled
    assert any("Objective forecast unavailable" in item.value for item in app.warning)
    assert not any("Expected hold after combat" in item.value for item in app.markdown)
    assert any("No valid forecast" in item.value for item in app.markdown)
