from pathlib import Path

from streamlit.testing.v1 import AppTest

from ww3.core.engine import new_game
from ww3.persistence.recovery import RecoveryStore


def test_legacy_checkpoint_is_copied_without_touching_the_original(tmp_path, monkeypatch):
    monkeypatch.delenv("WW3_SAVE_DIR")
    game = new_game()
    game.orders["EU"].tax_rate = .45
    legacy = RecoveryStore(tmp_path / ".saves")
    legacy.save(game, {"guide_enabled": False}, None)
    original = legacy.current.read_bytes()
    app_file = Path(__file__).resolve().parents[2] / "clients/streamlit/app.py"
    source = app_file.read_text().replace(
        "REPOSITORY = Path(__file__).resolve().parents[2]",
        f"REPOSITORY = Path({str(tmp_path)!r})",
    )
    app = AppTest.from_string(source, default_timeout=20).run()
    assert not app.exception
    assert app.session_state.game == game
    assert not app.session_state.guide_enabled
    assert RecoveryStore(tmp_path / ".saves/streamlit").recover().game == game
    assert legacy.current.read_bytes() == original
