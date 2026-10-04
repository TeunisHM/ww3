from copy import deepcopy
import json

import pytest

from ww3.core.ai import prepare_ai_orders
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import new_game, resolve_round
from ww3.core.forecast import forecast_round
from ww3.persistence import dumps, loads
from ww3.application.planning import DraftHistory, changed_decisions
from ww3.core.reporting import PHASES, message_phase, phase_messages
from ww3.core.strategy import objective_progress, theater_snapshot


@pytest.mark.parametrize("mode", ["solo", "sandbox", "hotseat"])
def test_theater_predictions_match_resolution_and_objectives(mode):
    game = new_game(mode)
    game.orders["EU"].deployments = dict(zip(FRONTS, [70, 0, 40, 0]))
    game.orders["EU"].alliance_offers = ["US"]
    game.orders["US"].alliance_offers = ["EU"]
    before = deepcopy(game)
    prediction = forecast_round(game)
    result = resolve_round(prepare_ai_orders(game))
    assert game == before
    for front in FRONTS:
        assert prediction["fronts"][front]["expected"] == theater_snapshot(result, front)
    for f in FACTIONS:
        assert prediction["objectives"][f] == objective_progress(result, f)
    assert prediction["streaks"] == result.objective_streaks
    assert prediction["fronts"][FRONTS[0]]["planned"]["factions"]["EU"]["upkeep"] == pytest.approx(.35)


def test_report_has_real_ordered_phases_and_traceable_faction_headlines():
    game = new_game()
    game.orders["EU"].investments = {"factory": 10}
    result = resolve_round(prepare_ai_orders(game))
    report = result.reports[-1]
    assert list(report["phase_ends"]) == list(PHASES)
    assert [m for phase in PHASES for m in phase_messages(report, phase)] == report["messages"]
    assert "EU completed factory." in phase_messages(report, "orders")
    assert any("military losses" in text for text in phase_messages(report, "combat"))
    for f in FACTIONS:
        assert len(report["highlights"][f]) == 3
        for index in report["highlights"][f]:
            assert report["messages"][index].startswith(f + ":")
            assert report["messages"][index] in phase_messages(report, message_phase(report, index))
        assert any(f"→ {result.nations[f].currency:.3f} T" in text for text in phase_messages(report, "economy"))
    assert loads(dumps(result)) == result


def test_legacy_v2_load_preserves_reports_without_fabricating_phases():
    game = resolve_round(prepare_ai_orders(new_game()))
    data = game.to_dict()
    data["schema_version"] = 2
    data.pop("rules_version")
    for report in data["reports"]:
        report.pop("phase_ends")
        report.pop("highlights")
    loaded = loads(json.dumps(data))
    assert loaded.reports[0]["messages"] == game.reports[0]["messages"]
    assert phase_messages(loaded.reports[0], "economy") == []
    assert loads(dumps(loaded)) == loaded


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(rules_version="future"),
    lambda d: d["reports"][0]["phase_ends"].update(combat=-1),
    lambda d: d["reports"][0]["highlights"].update(EU=[999999]),
])
def test_reject_invalid_rules_version_or_report_indices(mutation):
    data = resolve_round(prepare_ai_orders(new_game())).to_dict()
    mutation(data)
    with pytest.raises(ValueError):
        loads(json.dumps(data))


def test_undo_restores_each_factions_previous_edit_without_changing_world():
    game = new_game("sandbox")
    original = deepcopy(game.nations)
    history = DraftHistory(game)
    game.orders["EU"].investments = {"factory": 10}
    history.record(game, "EU")
    game.orders["US"].tax_rate = .5
    history.record(game, "US")
    game.orders["EU"].investments["research"] = 10  # deliberately invalid total
    history.record(game, "EU")
    assert len(changed_decisions(game, "EU")) == 2
    assert history.restore(game, "EU")
    assert game.orders["EU"].investments == {"factory": 10}
    assert game.orders["US"].tax_rate == .5
    game.submitted.append("EU")
    assert not history.restore(game, "EU")
    assert game.nations == original
