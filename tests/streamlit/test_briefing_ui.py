from copy import deepcopy
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ww3.core.catalog import FRONTS

APP = str(Path(__file__).resolve().parents[2] / "clients/streamlit/app.py")


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
