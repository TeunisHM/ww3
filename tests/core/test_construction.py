from copy import deepcopy

import pytest

from ww3.core.construction import construction_rows
from ww3.core.engine import EPS, InvalidOrder, new_game, resolve_round
from ww3.core.forecast import forecast_round
from ww3.core.models import pair


def construction(game, faction="EU"):
    return {row["key"]: row for row in forecast_round(game)["factions"][faction]["construction"]}


def test_draft_is_not_existing_work_and_forecast_does_not_mutate_it():
    game = new_game(mode="sandbox")
    game.orders["EU"].investments = {"factory": 5}
    original = deepcopy(game)
    row = construction(game)["factory"]
    assert game == original
    assert row["current_count"] == row["expected_count"] == 0
    assert row["current_progress"] == 0
    assert row["allocated_work"] == row["remaining_work"] / 2 == 5
    assert row["completed"] == 0
    assert row["started"] == 1
    assert row["forecast_valid"]
    assert row["expected_progress"] == .5
    assert row["expected_remaining_work"] == 5


def test_carried_work_pauses_without_an_allocation_and_finishes_when_funded():
    game = new_game(mode="sandbox")
    game.orders["EU"].investments = {"factory": 5}
    game = resolve_round(game)
    paused = construction(game)["factory"]
    assert paused["current_progress"] == paused["expected_progress"] == .5
    assert paused["remaining_work"] == paused["expected_remaining_work"] == 5
    assert paused["allocated_work"] == paused["completed"] == 0
    assert paused["started"] == 0

    game.orders["EU"].investments = {"factory": 5}
    # An already-paid unit can finish even with an empty treasury.
    game.nations["EU"].currency = 0
    finished = construction(game)["factory"]
    assert finished["completed"] == finished["expected_count"] == 1
    assert finished["started"] == 0
    assert finished["expected_progress"] == finished["expected_remaining_work"] == 0
    forecast = forecast_round(game)
    productivity = next(row for row in forecast["factions"]["EU"]["resources"] if row["key"] == "productivity")
    assert productivity["expected"] == 15


@pytest.mark.parametrize("key", ["factory", "civil_investment", "infrastructure"])
def test_bulk_work_counts_whole_units_and_only_the_unfinished_tail(key):
    game = new_game(mode="sandbox")
    game.nations["EU"].productivity = 100
    game.nations["EU"].progress[key] = .5
    work = 20 if key == "infrastructure" else 10
    game.orders["EU"].investments = {key: work * 2}
    row = construction(game)[key]
    assert row["completed"] == 2
    assert row["started"] == 2
    assert row["current_progress"] == row["expected_progress"] == .5
    assert row["expected_remaining_work"] == work / 2
    assert row["kind"] == ("building" if key == "factory" else "project")
    assert row["expected_count"] == (2 if key == "factory" else None)


@pytest.mark.parametrize("key", ["factory", "civil_investment"])
def test_completion_uses_engine_epsilon_instead_of_flooring_work(key):
    game = new_game(mode="sandbox")
    game.nations["EU"].productivity = 20
    game.orders["EU"].investments = {key: 20 - EPS * 5}
    row = construction(game)[key]
    assert row["completed"] == 2
    assert row["expected_progress"] == 0
    assert row["expected_remaining_work"] == 0


def test_mutual_trade_changes_data_center_work_before_construction():
    game = new_game(mode="sandbox")
    game.orders["US"].trade_offers = ["EU"]
    game.orders["EU"].trade_offers = ["US"]
    game.nations["US"].progress["datacenter"] = .5
    game.orders["US"].investments = {"datacenter": 3.75}
    row = construction(game, "US")["datacenter"]
    assert row["work_per_unit"] == 7.5
    assert row["remaining_work"] == 3.75
    assert row["completed"] == 1
    assert row["expected_count"] == game.nations["US"].buildings["datacenter"] + 1
    assert row["expected_remaining_work"] == 0


def test_withdrawn_trade_reprices_remaining_work_without_losing_progress():
    game = new_game(mode="sandbox")
    game.trades = [pair("EU", "US")]
    game.orders["US"].trade_offers = ["EU"]
    game.nations["US"].progress["datacenter"] = .5
    game.orders["US"].investments = {"datacenter": 3.75}
    row = construction(game, "US")["datacenter"]
    assert row["work_per_unit"] == 10
    assert row["remaining_work"] == 5
    assert row["completed"] == 0
    assert row["expected_progress"] == .875
    assert row["expected_remaining_work"] == 1.25


def test_invalid_plan_has_no_predicted_completion_or_progress():
    game = new_game(mode="sandbox")
    game.orders["EU"].investments = {"factory": 10}
    assert construction(game)["factory"]["completed"] == 1
    game.nations["EU"].currency = 0
    original = deepcopy(game)
    with pytest.raises(InvalidOrder):
        forecast_round(game)
    rows = construction_rows(game, "EU")
    row = next(row for row in rows if row["key"] == "factory")
    assert row["current_count"] == row["current_progress"] == 0
    assert row["allocated_work"] == row["remaining_work"] == 10
    assert all(row[field] is None for row in rows for field in (
        "completed", "started", "expected_count", "expected_progress", "expected_remaining_work",
    ))
    assert not any(row["forecast_valid"] for row in rows)
    assert game == original
