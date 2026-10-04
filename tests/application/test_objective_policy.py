from copy import deepcopy

import pytest

from ww3.core.catalog import FACTIONS
from ww3.core.engine import new_game, resolve_round
from ww3.evaluation import replay_campaign, run_campaign, scripted_orders
from ww3.objective_policy import _progress
from ww3.core.strategy import objective_progress


@pytest.mark.parametrize("faction", FACTIONS)
def test_objective_policy_can_complete_all_conditions_with_sufficient_power(faction):
    game = new_game(player=faction)
    # A public scenario with enough power to meet every condition. This catches
    # policies that focus exclusively on one front and overlook another goal.
    game.nations[faction].military = 6000
    game.nations[faction].military_capacity = 6000
    game.fronts["Eastern Europe"].influence["Russia"] = 0
    before = deepcopy(game)
    prepared = scripted_orders(game, "objective")
    assert game == before
    assert prepared.history == game.history
    resolved = resolve_round(prepared)
    assert all(row["met"] for row in objective_progress(resolved, faction))
    assert resolved.objective_streaks[faction] == 1


def test_objective_campaign_records_are_reproducible_and_replay_real_orders(tmp_path):
    first, records = run_campaign("Russia", "objective-industry", 23, 3, directory=tmp_path / "run")
    repeated, repeated_records = run_campaign("Russia", "objective-industry", 23, 3)
    assert (first, records) == (repeated, repeated_records)
    assert replay_campaign(tmp_path / "run")["verified_years"] == 3
    assert len(records[-1]["metrics"]["Russia"]["objectives"]) == 2


def test_partial_progress_respects_disqualified_security_coalitions():
    game = new_game(player="EU")
    game.alliances = ["EU|Russia"]
    assert objective_progress(game, "EU")[0]["value"] == 0
    assert _progress(game, "EU")[0] == 0
