import json
import pytest
from ww3.core.engine import new_game
from ww3.core.forecast import forecast_round
from ww3.persistence.preferences import DEFAULTS
from ww3.persistence.recovery import RecoveryStore, decode, encode


def test_settings_survive_recovery_without_changing_gameplay(tmp_path):
    store = RecoveryStore(tmp_path)
    game = new_game("hotseat")
    preferences = {**DEFAULTS, "sound_enabled": True, "sound_volume": 55, "text_scale": 150}
    store.save(game, preferences, None)
    recovered = store.recover()
    assert recovered.ui == preferences
    assert recovered.game == game
    assert forecast_round(recovered.game) == forecast_round(game)


@pytest.mark.parametrize("name,value", [("text_scale", 10000), ("sound_volume", -1), ("sound_volume", 101), ("sound_enabled", "true"), ("reduce_motion", 1)])
def test_invalid_preferences_cannot_be_loaded_as_css_or_audio_values(name, value):
    data = json.loads(encode(new_game(), DEFAULTS))
    data["ui"][name] = value
    with pytest.raises(ValueError, match="preferences"):
        decode(json.dumps(data).encode())
