"""The desktop read model and scenario/presentation command boundary."""

import pytest

from ww3.application.command_view import PAGES
from ww3.application.session import GameSession
from ww3.bridge.worker import Worker
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import domestic_interest, investment_cost
from ww3.core.reporting import PHASES, phase_messages
from ww3.core.rules import INVESTMENTS
from ww3.core.strategy import objective_progress


def call(worker, command, params=None):
    count = getattr(worker, "_test_requests", 0) + 1
    worker._test_requests = count
    return worker.handle({"protocol_version": 1, "id": str(count), "command": command,
                          "params": params or {}, "expected_revision": worker.session.revision})


def test_desktop_read_model_uses_authoritative_costs_objectives_and_forecasts(tmp_path):
    worker = Worker(tmp_path)
    before = worker.session.export()
    result = call(worker, "state")["result"]
    game = worker.session.snapshot()
    assert list(result["catalog"]["investments"]) == list(INVESTMENTS)
    for faction in FACTIONS:
        data = result["desk"]["factions"][faction]
        assert data["costs"] == {key: investment_cost(game, faction, key) for key in INVESTMENTS}
        assert data["domestic_interest"] == domestic_interest(game, faction)
        assert [item["current"] for item in data["objectives"]] == objective_progress(game, faction)
        assert data["construction"] == result["forecast"]["factions"][faction]["construction"]
    assert list(result["desk"]["fronts"]) == list(FRONTS)
    assert result["catalog"]["pages"] == list(PAGES)
    assert worker.session.export() == before
    result["catalog"]["government_effects"]["Democratic/pluralistic"]["content"] = 999
    assert call(worker, "state")["result"]["catalog"]["government_effects"]["Democratic/pluralistic"]["content"] == 1


def test_full_scenario_settings_round_trip_and_new_campaign_keeps_preferences(tmp_path):
    worker = Worker(tmp_path)
    assert call(worker, "ui", {"values": {"sound_enabled": True, "text_scale": 150, "page": PAGES[4]}})["ok"]
    rules = {"victory_mode": "influence", "victory_target": 300, "combat_attrition": .23,
             "influence_gain": 15, "hostility_drift": .06, "contract_years": 2,
             "government_transition_years": 4, "military_upkeep": .009,
             "objective_hold_years": 5, "ai_seed": 982,
             "starting_capital": dict.fromkeys(FACTIONS, 321),
             "starting_energy": dict.fromkeys(FACTIONS, 234),
             "starting_minerals": dict.fromkeys(FACTIONS, 123),
             "starting_content": dict.fromkeys(FACTIONS, 67)}
    reply = call(worker, "new", {"mode": "sandbox", "player": "Russia", "rules": rules})
    assert reply["ok"], reply
    game = worker.session.snapshot()
    for key, value in rules.items():
        assert getattr(game.rules, key) == value
    assert all(n.currency == 321 and n.minerals == 123 and n.energy == 234 and n.content == 67 for n in game.nations.values())
    ui = reply["result"]["ui"]
    assert ui["commander"] == "Russia" and ui["page"] == PAGES[0]
    assert ui["sound_enabled"] and ui["text_scale"] == 150
    exported = call(worker, "export")["result"]["save"]
    recovered = GameSession.new()
    recovered.load(exported)
    assert recovered.snapshot() == game
    assert recovered.forecast() == worker.session.forecast()


@pytest.mark.parametrize("rules", [
    {"combat_attrition": .51}, {"ai_seed": True}, {"ai_seed": 1.5}, {"ai_seed": 100001},
    {"military_upkeep": -1}, {"contract_years": 0}, {"objective_hold_years": 11},
    {"government_transition_years": 2.0}, {"victory_mode": "unknown"},
    {"victory_target": 401}, {"starting_capital": {"EU": 1}},
    {"starting_energy": dict.fromkeys(FACTIONS, 1001)},
    {"starting_content": dict.fromkeys(FACTIONS, -1)}, {"unexpected": 1}, [1],
])
def test_invalid_scenario_is_atomic(tmp_path, rules):
    worker = Worker(tmp_path)
    call(worker, "edit", {"faction": "EU", "changes": {"tax_rate": .33}})
    before, revision = worker.session.export(), worker.session.revision
    checkpoint = worker.store.current.read_bytes()
    assert not call(worker, "new", {"rules": rules})["ok"]
    assert worker.session.export() == before and worker.session.revision == revision
    assert worker.store.current.read_bytes() == checkpoint


def test_ui_recovery_is_independent_of_portable_save_and_turns(tmp_path):
    worker = Worker(tmp_path)
    before = worker.session.export()
    values = {"page": PAGES[3], "selected_front": FRONTS[2], "text_scale": 130,
              "sound_enabled": True, "sound_volume": 65, "reduce_motion": False,
              "guide_enabled": False, "review_step": 4, "review_open": True}
    reply = call(worker, "ui", {"values": values})
    assert reply["ok"] and reply["revision"] == 0
    assert worker.session.export() == before
    reopened = Worker(tmp_path)
    assert reopened.session.export() == before
    assert all(reopened.ui[key] == value for key, value in values.items())
    for invalid in ({"sound_volume": 101}, {"text_scale": 101}, {"review_step": 6},
                    {"handoff": 1}, {"commander": "unknown"}, {"page": "oops"}, {"rule": 4}):
        old = reopened.ui.copy()
        assert not call(reopened, "ui", {"values": invalid})["ok"]
        assert reopened.ui == old


def test_hotseat_handoff_and_review_are_checkpointed_with_the_turn(tmp_path):
    worker = Worker(tmp_path)
    assert call(worker, "new", {"mode": "hotseat", "player": "China"})["ok"]
    call(worker, "commit", {"faction": "China"})
    worker = Worker(tmp_path)
    assert worker.ui["handoff"] and worker.ui["commander"] == "EU"
    assert worker.session.snapshot().submitted == ["China"]
    for faction in ("EU", "US", "Russia"):
        reply = call(worker, "commit", {"faction": faction})
        assert reply["ok"], reply
    worker = Worker(tmp_path)
    assert worker.session.snapshot().round == 2
    assert worker.ui["handoff"] and worker.ui["review_open"] and worker.ui["review_step"] == 0
    result = call(worker, "state")["result"]
    report = worker.session.snapshot().reports[-1]
    assert result["desk"]["review"]["grouped"]
    for item, phase in zip(result["desk"]["review"]["phases"], PHASES):
        assert item["messages"] == phase_messages(report, phase)
    before = worker.session.export()
    for step in range(6):
        call(worker, "ui", {"values": {"review_step": step}})
    assert worker.session.export() == before


def test_invalid_draft_read_model_retains_facts_clears_predictions_and_compares_safely(tmp_path):
    worker = Worker(tmp_path)
    call(worker, "remember", {"faction": "EU"})
    reply = call(worker, "edit", {"faction": "EU", "changes": {"investments": {"factory": 100}}})
    data = reply["result"]
    assert data["forecast"] is None and data["desk"]["factions"]["EU"]["plan_error"]
    assert all(item["expected"] is None for item in data["desk"]["factions"]["EU"]["objectives"])
    assert all(item["completed"] is None for item in data["desk"]["factions"]["EU"]["construction"])
    comparison = call(worker, "compare", {"faction": "EU"})["result"]
    assert comparison["current"]["error"] and comparison["remembered"]["forecast"]
    call(worker, "restore", {"faction": "EU"})
    assert call(worker, "state")["result"]["forecast"] is not None
    assert call(worker, "undo", {"faction": "EU"})["result"]["forecast"] is None
