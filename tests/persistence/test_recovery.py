from copy import deepcopy
import pytest
from ww3.core.catalog import FRONTS
from ww3.core.engine import new_game
from ww3.persistence import dumps, loads
from ww3.persistence.recovery import RecoveryConflict, RecoveryStore, decode, encode


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
    import ww3.persistence.recovery as recovery
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
