"""Validated presentation values, kept separate from gameplay rules."""

DEFAULTS = {"sound_enabled": False, "sound_volume": 30, "text_scale": 100, "reduce_motion": True}
TEXT_SCALES = (100, 115, 130, 150)


def valid_preferences(values):
    for name in DEFAULTS:
        if name not in values:
            continue
        value = values[name]
        if name in ("sound_enabled", "reduce_motion"):
            if type(value) is not bool:
                return False
        elif type(value) is not int or (value not in TEXT_SCALES if name == "text_scale" else not 0 <= value <= 100):
            return False
    return True
