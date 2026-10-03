from copy import deepcopy
import json

import pytest

from ww3.ai import prepare_ai_orders
from ww3.catalog import FACTIONS, FRONTS
from ww3.engine import new_game, resolve_round
from ww3.forecast import forecast_round
from ww3.persistence import dumps, loads
from ww3.planning import DraftHistory, changed_decisions
from ww3.recovery import RecoveryConflict, RecoveryStore, decode, encode
from ww3.reporting import PHASES, message_phase, phase_messages
from ww3.strategy import objective_progress, theater_snapshot


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


def test_recovery_restores_invalid_drafts_and_hotseat_commitments(tmp_path):
    store = RecoveryStore(tmp_path)
    game = new_game("hotseat")
    game.submitted = ["US"]
    game.orders["EU"].investments = {"factory": 10, "research": 10}
    game.orders["EU"].deployments = dict.fromkeys(FRONTS, game.nations["EU"].military)
    ui = {"commander": "EU", "handoff": True, "guide_enabled": False}
    token = store.save(game, ui, None)
    restored = store.recover()
    assert restored.game == game and restored.ui == ui and restored.token == token
    with pytest.raises(ValueError):
        loads(dumps(game))
    game.submitted.append("EU")
    with pytest.raises(ValueError):
        encode(game, ui)


def test_corrupt_latest_falls_back_and_never_replaces_valid_backup(tmp_path):
    store = RecoveryStore(tmp_path)
    opening = new_game()
    token = store.save(opening, {}, None)
    edited = deepcopy(opening)
    edited.orders["EU"].tax_rate = .5
    store.save(edited, {}, token)
    store.current.write_bytes(b'{"interrupted":')
    recovered = store.recover()
    assert recovered.game == opening and "previous" in recovered.warning
    store.save(opening, {}, recovered.token)
    assert decode(store.previous.read_bytes())[0] == opening
    assert store.recover().game == opening


@pytest.mark.parametrize("failing_path", ["current", "previous"])
def test_interrupted_atomic_write_preserves_valid_checkpoint(tmp_path, monkeypatch, failing_path):
    store = RecoveryStore(tmp_path)
    game = new_game()
    token = store.save(game, {}, None)
    original = store.current.read_bytes()
    edited = deepcopy(game)
    edited.orders["EU"].tax_rate = .5
    import ww3.recovery as recovery
    replace = recovery.os.replace

    def fail(source, target):
        if target == getattr(store, failing_path):
            raise OSError("Simulated disk write failure")
        replace(source, target)

    monkeypatch.setattr(recovery.os, "replace", fail)
    with pytest.raises(OSError):
        store.save(edited, {}, token)
    assert store.current.read_bytes() == original
    assert store.recover().game == game
    assert not list(tmp_path.glob(".pending-*"))


def test_old_session_cannot_overwrite_newer_campaign(tmp_path):
    store = RecoveryStore(tmp_path)
    game = new_game()
    token = store.save(game, {}, None)
    game.orders["EU"].tax_rate = .5
    latest = store.save(game, {}, token)
    with pytest.raises(RecoveryConflict):
        store.save(new_game(), {}, token)
    assert store.recover().token == latest


def test_both_corrupt_checkpoints_have_explicit_manual_recovery_path(tmp_path):
    store = RecoveryStore(tmp_path)
    store.current.write_bytes(b'broken')
    store.previous.write_bytes(b'broken too')
    restored = store.recover()
    assert restored.game is None
    assert "Import a manual save" in restored.warning
    store.save(new_game(), {}, restored.token)
    assert store.recover().game == new_game()


def test_valid_current_does_not_require_readable_previous_file(tmp_path, monkeypatch):
    store = RecoveryStore(tmp_path)
    store.save(new_game(), {}, None)
    read = store._read

    def unreadable_previous(path):
        if path == store.previous:
            raise PermissionError("Unreadable previous checkpoint")
        return read(path)

    monkeypatch.setattr(store, "_read", unreadable_previous)
    assert store.recover().game == new_game()
