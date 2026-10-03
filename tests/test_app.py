from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ww3.catalog import FACTIONS, FRONTS

APP = str(Path(__file__).parents[1] / "app.py")


def start(mode=None, faction="EU"):
    app = AppTest.from_file(APP, default_timeout=20).run()
    assert not app.exception
    app.button(key="customize_intro").click().run()
    if mode:
        app.radio(key="setup_mode").set_value(mode)
    app.selectbox(key="setup_faction").set_value(faction).run()
    app.button(key="start_game").click().run()
    assert not app.exception
    return app


def widget_key(app, faction, name):
    return f"{app.session_state.epoch}:{app.session_state.game.round}:{faction}:{name}"


def test_all_command_screens_render_without_advancing_time():
    app = start()
    for page in ("Economy & construction", "Diplomacy", "Military fronts", "Government & debt", "Objectives", "Chronicle", "Rules & reference", "Situation room"):
        app.radio(key="page").set_value(page).run()
        assert not app.exception, (page, app.exception)
        assert app.session_state.game.round == 1


def test_player_can_build_change_tax_and_deploy_in_one_turn():
    app = start()
    app.radio(key="page").set_value("Economy & construction").run()
    app.number_input(key=widget_key(app, "EU", "factory")).set_value(10.0).run()
    app.radio(key="page").set_value("Government & debt").run()
    app.slider(key=widget_key(app, "EU", "tax")).set_value(35.0).run()
    app.radio(key="page").set_value("Military fronts").run()
    app.number_input(key=widget_key(app, "EU", f"deploy_{FRONTS[0]}")).set_value(30.0).run()
    app.button(key="end_year").click().run()
    assert not app.exception
    game = app.session_state.game
    assert game.round == 2
    assert game.nations["EU"].buildings["factory"] == 1
    assert game.nations["EU"].tax_rate == .35
    assert 0 <= game.nations["EU"].deployments[FRONTS[0]] <= 30
    assert any(n.buildings["factory"] != game.rules.starting_buildings[f]["factory"] or n.military != {"US": 400, "China": 200, "Russia": 200}[f] for f, n in game.nations.items() if f != "EU")


def test_ui_blocks_overallocated_productivity():
    app = start()
    app.radio(key="page").set_value("Economy & construction").run()
    app.number_input(key=widget_key(app, "EU", "factory")).set_value(10.0).run()
    app.number_input(key=widget_key(app, "EU", "research")).set_value(10.0).run()
    assert app.button(key="end_year").disabled
    assert any("productivity" in e.value.lower() for e in app.error)
    app.button(key="clear_draft").click().run()
    assert not app.button(key="end_year").disabled


def test_four_hotseat_submissions_resolve_one_shared_round():
    app = start("Local hotseat · four players")
    for turn in range(4):
        app.button(key="end_year").click().run()
        assert not app.exception
        assert app.session_state.game.round == (2 if turn == 3 else 1)
        button = next(b for b in app.button if b.label == "Open command desk")
        button.click().run()
        assert not app.exception
    assert app.session_state.game.submitted == []
    assert len(app.session_state.game.reports) == 1


def test_sandbox_switches_factions_and_preserves_drafts():
    app = start("Sandbox · control all factions")
    app.radio(key="page").set_value("Military fronts").run()
    app.number_input(key=widget_key(app, "EU", f"deploy_{FRONTS[0]}")).set_value(20.0).run()
    selector = next(s for s in app.selectbox if s.label == "Command faction")
    selector.set_value("US").run()
    app.number_input(key=widget_key(app, "US", f"deploy_{FRONTS[1]}")).set_value(40.0).run()
    app.button(key="end_year").click().run()
    assert not app.exception
    game = app.session_state.game
    assert game.round == 2
    assert 0 < game.nations["EU"].deployments[FRONTS[0]] <= 20
    assert 0 < game.nations["US"].deployments[FRONTS[1]] <= 40
    assert game.fronts[FRONTS[0]].influence["EU"] == 35
    assert game.fronts[FRONTS[1]].influence["US"] == 40


def test_live_resource_forecast_updates_and_matches_end_year():
    app = start()
    first = float([m.value for m in app.metric if m.label == "Treasury · T USD"][-1].replace(",", ""))
    app.radio(key="page").set_value("Government & debt").run()
    app.slider(key=widget_key(app, "EU", "tax")).set_value(50.0).run()
    second = float([m.value for m in app.metric if m.label == "Treasury · T USD"][-1].replace(",", ""))
    assert second > first
    assert app.session_state.game.round == 1
    app.button(key="end_year").click().run()
    assert not app.exception
    assert app.session_state.game.nations["EU"].currency == pytest.approx(second, abs=.005)


def test_objectives_screen_explains_opening_eu_conditions():
    app = start()
    app.radio(key="page").set_value("Objectives").run()
    assert not app.exception
    descriptions = [m.value for m in app.markdown]
    assert any("42.9%" in text for text in descriptions)
    assert any("45.0/100" in text for text in descriptions)
    assert app.session_state.game.objective_streaks["EU"] == 0


def test_map_selection_draft_summary_undo_and_reset_share_real_orders():
    app = start()
    for front in FRONTS:
        app.selectbox(key="front_selector").set_value(front).run()
        assert not app.exception
        assert app.session_state.selected_front == front
    app.number_input(key=widget_key(app, "EU", f"deploy_{FRONTS[0]}")).set_value(35.0).run()
    assert app.session_state.game.orders["EU"].deployments[FRONTS[0]] == 35
    assert any("changed decisions" in m.value for m in app.markdown)
    app.radio(key="page").set_value("Economy & construction").run()
    app.number_input(key=widget_key(app, "EU", "factory")).set_value(10.0).run()
    app.button(key="undo_draft").click().run()
    assert app.session_state.game.orders["EU"].investments == {}
    assert app.session_state.game.orders["EU"].deployments[FRONTS[0]] == 35
    app.button(key="clear_draft").click().run()
    assert app.session_state.game.orders["EU"].deployments == app.session_state.game.nations["EU"].deployments
    app.button(key="undo_draft").click().run()
    assert app.session_state.game.orders["EU"].deployments[FRONTS[0]] == 35


def test_relaunch_restores_invalid_draft_and_skipped_guidance():
    app = start()
    app.checkbox(key="guide_choice").uncheck().run()
    app.radio(key="page").set_value("Economy & construction").run()
    for building in ("factory", "research"):
        app.number_input(key=widget_key(app, "EU", building)).set_value(10.0).run()
    assert app.button(key="end_year").disabled
    restarted = AppTest.from_file(APP).run()
    assert not restarted.exception
    assert restarted.session_state.game.orders["EU"].investments == {"factory": 10, "research": 10}
    assert not restarted.checkbox(key="guide_choice").value
    assert restarted.button(key="end_year").disabled
    restarted.button(key="clear_draft").click().run()
    assert not restarted.button(key="end_year").disabled


def test_hotseat_relaunch_keeps_handoff_and_locked_orders():
    app = start("Local hotseat · four players")
    app.button(key="end_year").click().run()
    restarted = AppTest.from_file(APP).run()
    assert not restarted.exception
    assert restarted.session_state.game.submitted == ["EU"]
    assert restarted.session_state.commander == "US"
    assert restarted.session_state.handoff
    next(b for b in restarted.button if b.label == "Open command desk").click().run()
    selector = next(s for s in restarted.selectbox if s.label == "Command faction")
    selector.set_value("EU").run()
    assert restarted.button(key="undo_draft").disabled
    assert restarted.button(key="clear_draft").disabled
    assert restarted.button(key="end_year").disabled


def test_three_year_guidance_and_skippable_replay_do_not_advance_simulation():
    app = start()
    for round_number in range(1, 4):
        assert any(f"Year {round_number} of 3" in m.value for m in app.markdown)
        app.button(key="end_year").click().run()
        assert not app.exception
        assert app.session_state.game.round == round_number + 1
        app.button(key="skip_review").click().run()
        app.button(key="replay_results").click().run()
        assert app.session_state.game.round == round_number + 1
        app.button(key="skip_review").click().run()
    assert any("introduction is complete" in m.value for m in app.markdown)
    assert app.session_state.game.rules.objective_hold_years == 3


def test_explicit_previous_recovery_resynchronizes_controls():
    app = start()
    app.selectbox(key="front_selector").set_value("Arctic").run()
    # Keep the preceding checkpoint with guidance enabled, then skip it.
    app.checkbox(key="guide_choice").uncheck().run()
    app.button(key="previous_checkpoint").click().run()
    assert not app.exception
    assert app.selectbox(key="front_selector").value == "Arctic"
    assert app.checkbox(key="guide_choice").value


def test_intro_quick_start_and_preferences_survive_reload():
    app = AppTest.from_file(APP).run()
    assert app.button(key="quick_start")
    assert "game" not in app.session_state
    app.checkbox(key="setting_sound_enabled").check().run()
    app.slider(key="setting_sound_volume").set_value(55).run()
    app.select_slider(key="setting_text_scale").set_value(150).run()
    app.button(key="quick_start").click().run()
    assert not app.exception
    assert app.session_state.game.round == 1 and app.session_state.game.player == "EU"
    restarted = AppTest.from_file(APP).run()
    assert not restarted.exception
    assert restarted.checkbox(key="setting_sound_enabled").value
    assert restarted.slider(key="setting_sound_volume").value == 55
    assert restarted.select_slider(key="setting_text_scale").value == 150


def test_ui_remember_restore_undo_and_no_sound_repeated_on_navigation():
    app = start()
    app.button(key="remember_draft").click().run()
    app.radio(key="page").set_value("Government & debt").run()
    app.slider(key=widget_key(app, "EU", "tax")).set_value(50.0).run()
    sound = app.session_state.audio_event
    assert sound["kind"] == "order"
    app.radio(key="page").set_value("Military fronts").run()
    assert app.session_state.audio_event == sound
    app.button(key="restore_remembered").click().run()
    assert app.session_state.game.orders["EU"].tax_rate == .4
    app.button(key="undo_draft").click().run()
    assert app.session_state.game.orders["EU"].tax_rate == .5
    app.button(key="end_year").click().run()
    assert not app.exception
    assert not app.session_state.draft_history.remembered
    assert app.session_state.audio_event["kind"] == "resolve"


def test_rerun_immediately_after_checkpoint_write_keeps_recovery_current(monkeypatch):
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    from streamlit.runtime.scriptrunner_utils.script_requests import RerunData
    from ww3.recovery import RecoveryStore

    app = start()
    original = RecoveryStore.save
    interrupted = []

    def save_then_request_rerun(store, game, ui, token):
        result = original(store, game, ui, token)
        if not interrupted:
            interrupted.append(True)
            get_script_run_ctx().script_requests.request_rerun(RerunData())
        return result

    monkeypatch.setattr(RecoveryStore, "save", save_then_request_rerun)
    app.radio(key="page").set_value("Economy & construction").run()
    assert not app.exception
    assert "checkpoint_error" not in app.session_state
    app.number_input(key=widget_key(app, "EU", "factory")).set_value(10).run()
    app.button(key="end_year").click().run()
    assert not app.exception
    resumed = AppTest.from_file(APP).run()
    assert not resumed.exception
    assert resumed.session_state.game.round == 2
    assert resumed.session_state.game.nations["EU"].productivity == 15
