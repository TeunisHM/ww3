"""Run with: streamlit run app.py"""

from dataclasses import asdict
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from ww3.application.session import GameSession
from ww3.core.catalog import COLORS, FACTIONS, FRONTS, GOVERNMENTS, SCENARIO, TRAITS
from ww3.core.engine import InvalidOrder, domestic_interest, investment_cost, new_game, preview_plan
from ww3_streamlit.command_ui import cached_forecast, command_theater, decision_briefing, draft_comparison, guided_opening, key, objective_dashboard, planning_summary, projection, turn_review
from ww3.core.construction import construction_rows
from ww3_streamlit.construction_ui import construction_card, construction_overview, work_percent
from ww3_streamlit.map_view import render_map
from ww3_streamlit.intro import render_opening
from ww3.core.models import pair
from ww3.persistence import dumps, loads
from ww3.persistence.recovery import RecoverySession, RecoveryStore, UI_KEYS
from ww3_streamlit.presentation import DEFAULTS as PRESENTATION_DEFAULTS, apply_display, cue, render_audio, settings_controls
from ww3.core.rules import BUILDINGS, GOVERNMENT_EFFECTS, INVESTMENTS, PROJECTS, Rules
from ww3.core.strategy import OBJECTIVE_NAMES, dominance, dominance_bonus, objective_progress

st.set_page_config(page_title="Geopolitics · WW3", page_icon="◈", layout="wide", initial_sidebar_state="auto")
st.markdown("""<style>
.block-container {max-width:1450px; padding-top:2rem; padding-bottom:3rem;}
h1 {letter-spacing:-.045em; font-weight:750 !important;}
h2,h3 {letter-spacing:-.025em;}
[data-testid="stMetric"] {background:#141e2a; border:1px solid #283847; border-radius:9px; padding:14px 16px;}
[data-testid="stMetricLabel"] {color:#9cb0c2;}
[data-testid="stMetricValue"] {font-size:1.7rem;}
[data-testid="stSidebar"] {border-right:1px solid #283847;}
.eyebrow {color:#71d6bc; text-transform:uppercase; letter-spacing:.2em; font-size:.7rem; margin-bottom:.3rem;}
.muted {color:#95a9ba; font-size:.93rem;}
.faction-tag {display:inline-block; padding:4px 10px; border-radius:5px; border:1px solid #344959; font-size:.8rem; margin-bottom:.6rem;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:10px;}
[data-testid="stAppDeployButton"] {display:none;}
div:has(> .st-key-planning_summary) {position:sticky; top:3.5rem; z-index:10;}
.st-key-planning_summary {background:#101b27; border:1px solid #344959; border-radius:10px; padding:.65rem 1rem; box-shadow:0 5px 20px #0006;}
.st-key-planning_summary [data-testid="stVerticalBlock"] {gap:.3rem;}
.resource-scroll {overflow-x:auto;}
.resource-summary {width:100%; font-size:.78rem; font-variant-numeric:tabular-nums; white-space:nowrap; border-collapse:collapse;}
.resource-summary td,.resource-summary th {padding:.2rem .4rem; text-align:right; border-bottom:1px solid #283847;}
.resource-summary th:first-child {text-align:left;}
.resource-summary thead {color:#9cb0c2;}
.resource-summary tr:last-child {color:#71d6bc; font-weight:700;}
.sr-only {position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0;}
@media (max-width:900px) {div:has(> .st-key-planning_summary) {position:static;}}
@media (max-height:750px) {.resource-summary {font-size:.7rem;} .st-key-planning_summary {padding:.35rem .6rem;}}
@media (max-width:640px) {.block-container {padding:1.5rem 1rem 2rem;}}
</style>""", unsafe_allow_html=True)

MODES = {"One faction vs computer opponents": "solo", "Local hotseat · four players": "hotseat", "Sandbox · control all factions": "sandbox"}
PAGES = ["Situation room", "Economy & construction", "Diplomacy", "Military fronts", "Government & debt", "Objectives", "Chronicle", "Rules & reference"]
REPOSITORY = Path(__file__).resolve().parents[2]


def sync_session():
    session = st.session_state.game_session
    st.session_state.game = session.snapshot()
    st.session_state.draft_history = session.draft_history


def set_game(game):
    st.session_state.game_session = GameSession(game)
    sync_session()
    st.session_state.epoch = st.session_state.get("epoch", 0) + 1
    st.session_state.commander = game.player
    st.session_state.handoff = False
    st.session_state.review_open = False
    st.session_state.review_step = 0
    st.session_state.setdefault("guide_enabled", True)
    st.session_state.setdefault("selected_front", FRONTS[0])
    st.session_state.pop("audio_event", None)


def recovery_store():
    if os.environ.get("WW3_SAVE_DIR"):
        return RecoveryStore(os.environ["WW3_SAVE_DIR"])
    directory = REPOSITORY / ".saves" / "streamlit"
    # Preserve the existing local campaign on its first launch after migration.
    store = RecoveryStore(directory)
    if not store.current.exists() and not store.previous.exists():
        legacy = RecoveryStore(REPOSITORY / ".saves").recover()
        if legacy.game is not None:
            store.save(legacy.game, legacy.ui, None)
    return store


def restore_checkpoint(previous=False):
    try:
        recovered = recovery_store().recover(previous=previous)
        st.session_state.recovery_session = RecoverySession(recovered.token)
        st.session_state.recovery_notice = recovered.warning
        if recovered.game:
            set_game(recovered.game)
            for name, value in (recovered.ui or {}).items():
                if name == "page" and value not in PAGES or name == "selected_front" and value not in FRONTS or name == "commander" and value not in FACTIONS:
                    continue
                if name in ("guide_enabled", "handoff", "review_open") and type(value) is not bool:
                    continue
                if name == "review_step" and (type(value) is not int or not 0 <= value < 6):
                    continue
                st.session_state[name] = value
            # Native widgets can retain values from the current session even
            # when a checkpoint restores different presentation preferences.
            st.session_state.front_selector = st.session_state.selected_front
            st.session_state.guide_choice = st.session_state.guide_enabled
            for name, default in PRESENTATION_DEFAULTS.items():
                st.session_state.setdefault(name, default)
                st.session_state[f"setting_{name}"] = st.session_state[name]
            st.session_state.pop("checkpoint_error", None)
    except (OSError, ValueError) as exc:
        st.session_state.checkpoint_error = f"Could not read automatic recovery: {exc}"


def checkpoint(game):
    ui = {name: st.session_state[name] for name in UI_KEYS if name in st.session_state}
    # The cursor owns its disk token: a UI rerun cannot interrupt the assignment
    # after a successful write and leave this session permanently stale.
    st.session_state.setdefault("recovery_session", RecoverySession())
    recovery = st.session_state.recovery_session
    try:
        recovery.save(recovery_store(), game, ui)
        st.session_state.pop("checkpoint_error", None)
    except (OSError, ValueError) as exc:
        st.session_state.checkpoint_error = f"Automatic recovery could not save: {exc}"


def undo_draft(game, faction):
    if st.session_state.game_session.undo(faction):
        sync_session()
        st.session_state.epoch += 1
        cue("order")


def reset_draft(game, faction):
    if st.session_state.game_session.reset_draft(faction):
        sync_session()
        st.session_state.epoch += 1
        cue("order")


def remember_draft(game, faction):
    st.session_state.game_session.remember(faction)
    sync_session()
    cue("order")


def restore_remembered(game, faction):
    if st.session_state.game_session.restore_remembered(faction):
        sync_session()
        st.session_state.epoch += 1
        cue("order")


def intro_screen(resuming=False):
    with st.container(key="opening_briefing"):
        render_opening()
        with st.container(key="opening_actions"):
            if resuming:
                game = st.session_state.game
                if st.button("Continue campaign", type="primary", key="continue_campaign", width="stretch"):
                    st.session_state.show_opening_briefing = False
                    st.rerun()
                st.caption(f"Return to your {SCENARIO[game.player]['name']} campaign · {game.year} · Round {game.round}")
            else:
                quick, customize = st.columns(2)
                if quick.button("Start EU campaign", type="primary", key="quick_start", width="stretch"):
                    set_game(GameSession.new().snapshot())
                    checkpoint(st.session_state.game)
                    st.rerun()
                if customize.button("Choose faction & mode", key="customize_intro", width="stretch"):
                    st.session_state.intro_seen = True
                    st.rerun()
                st.caption("Solo, local hotseat or sandbox · Offline after installation · No campaign turn limit")
    if resuming:
        return
    with st.expander("Continue from a portable save"):
        uploaded = st.file_uploader("Saved campaign (.json)", type="json", key="intro_upload")
        if st.button("Load campaign", disabled=uploaded is None, key="intro_load"):
            try:
                set_game(loads(uploaded.getvalue(), allow_invalid_drafts=True))
            except ValueError as exc:
                st.error(str(exc))
            else:
                checkpoint(st.session_state.game)
                st.rerun()
    if st.session_state.get("recovery_notice"):
        st.warning(st.session_state.recovery_notice)
    if st.session_state.get("checkpoint_error"):
        st.warning(st.session_state.checkpoint_error)


def save_controls(game):
    with st.sidebar.expander("Save / load game"):
        st.download_button("Download save", dumps(game), f"ww3-{game.year}-round-{game.round}.json", "application/json", key="download_save", width="stretch", on_click="ignore")
        uploaded = st.file_uploader("Load a saved simulation", type="json", key="save_upload")
        if st.button("Load selected save", disabled=uploaded is None, width="stretch"):
            try:
                loaded = loads(uploaded.getvalue(), allow_invalid_drafts=True)
            except ValueError as exc:
                st.error(f"Could not load this save: {exc}")
            else:
                set_game(loaded)
                checkpoint(loaded)
                st.rerun()
        st.caption("Automatic recovery saves this local campaign, including drafts. Manual downloads are independent portable copies. Undo history lasts only for this open session and year.")
        st.button("Reload latest checkpoint", key="reload_checkpoint", on_click=restore_checkpoint, width="stretch")
        st.button("Recover previous checkpoint", key="previous_checkpoint", on_click=restore_checkpoint, args=(True,), width="stretch")
    if st.session_state.get("checkpoint_error"):
        st.sidebar.error(st.session_state.checkpoint_error)
    else:
        st.sidebar.caption("✓ Campaign and draft saved locally")
    if st.session_state.get("recovery_notice"):
        st.sidebar.warning(st.session_state.recovery_notice)


def setup():
    if st.session_state.get("recovery_notice"):
        st.warning(st.session_state.recovery_notice)
    if st.session_state.get("checkpoint_error"):
        st.warning(st.session_state.checkpoint_error)
    st.markdown('<div class="eyebrow">A turn-based geopolitical simulation</div>', unsafe_allow_html=True)
    st.title("GEOPOLITICS / WW3")
    st.write("Build an economy. Shape alliances. Contest the world's strategic fronts.")
    st.caption("Four factions, annual turns, and distinct strategic objectives. Secure your position and hold it for three years.")
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        mode_label = st.radio("How will you play?", list(MODES), key="setup_mode")
        faction = st.selectbox("Your starting faction", FACTIONS, format_func=lambda f: f"{f} · {SCENARIO[f]['name']}", key="setup_faction")
        source = SCENARIO[faction]
        st.info(source["brief"])
        for trait in TRAITS[faction]:
            st.write(f"• {trait}")
        c1, c2, c3 = st.columns(3)
        c1.metric("GDP", f"{source['gdp']:.1f} T")
        c2.metric("Debt", f"{source['debt']:.2f} T")
        c3.metric("Military", int(source["military"]))
    with right:
        st.image(render_map(new_game()), width="stretch")
        with st.container(border=True):
            st.markdown("**Your first year**")
            st.write("1. Invest productivity in facilities and projects.\n2. Offer agreements and set tariffs.\n3. Deploy military power to fronts.\n4. Adjust government, taxes, and debt.\n5. End the year to resolve every faction's orders.")
            st.caption("Plans stay editable until committed. Unspent productivity and compute expire; currency, energy, minerals, innovation, and military power accumulate.")
    rules = Rules()
    victory = st.selectbox("Victory rules", ["Faction objectives", "Open-ended simulation", "Total influence target"], key="setup_victory")
    rules.victory_mode = {"Faction objectives": "objectives", "Open-ended simulation": "open", "Total influence target": "influence"}[victory]
    if rules.victory_mode == "influence":
        rules.victory_target = st.slider("Influence target across all fronts", 150, 400, 250, 10)
    with st.expander("Your objectives & opening deployments", expanded=True):
        st.markdown(f"**{OBJECTIVE_NAMES[faction]}**")
        for objective in objective_progress(new_game(), faction):
            st.write(f"• {objective['condition']}")
        st.caption("Meet all conditions for three consecutive completed rounds. Progress is checked after combat; missing any condition resets the count.")
        st.dataframe([{"Faction": f, **rules.starting_deployments[f], "Reserve": SCENARIO[f]["military"] - sum(rules.starting_deployments[f].values())} for f in FACTIONS], hide_index=True, width="stretch")
    with st.expander("Scenario & balance settings"):
        st.caption("The full rulebook is available under Rules & reference. These settings let you tune a new scenario.")
        a, b, c = st.columns(3)
        rules.combat_attrition = a.slider("Combat strength-gap attrition (%)", 0, 50, 10, key="setup_attrition") / 100
        rules.influence_gain = b.slider("Influence gained per uncontested front", 1, 25, 10, key="setup_influence")
        rules.hostility_drift = c.slider("Annual relationship deterioration", 0.0, .2, .02, .01, key="setup_hostility")
        rules.contract_years = a.number_input("Debt contract length (years)", 1, 10, 3, key="setup_contract")
        rules.government_transition_years = b.number_input("Government transition (years)", 1, 10, 3, key="setup_transition")
        rules.military_upkeep = c.number_input("Military upkeep (T per deployed point)", 0.0, .02, .005, .001, format="%.3f", key="setup_military_cost")
        rules.objective_hold_years = a.number_input("Consecutive years required for victory", 1, 10, 3, key="setup_hold")
        rules.ai_seed = b.number_input("Computer strategy variation seed", 0, 100000, 17, key="setup_seed")
        st.caption("Starting assets follow the reconciled faction scenario.")
        for f, col in zip(FACTIONS, st.columns(4)):
            rules.starting_capital[f] = col.number_input(f"{f} treasury (T USD)", 0.0, 1000.0, rules.starting_capital[f], key=f"setup_capital_{f}")
            rules.starting_energy[f] = col.number_input(f"{f} energy (PJ)", 0.0, 1000.0, rules.starting_energy[f], key=f"setup_energy_{f}")
            rules.starting_minerals[f] = col.number_input(f"{f} minerals (t)", 0.0, 1000.0, rules.starting_minerals[f], key=f"setup_minerals_{f}")
            rules.starting_content[f] = col.slider(f"{f} citizen content", 0, 100, int(rules.starting_content[f]), key=f"setup_content_{f}")
    if st.button("Take command", type="primary", key="start_game", width="stretch"):
        set_game(GameSession.new(MODES[mode_label], faction, rules).snapshot())
        checkpoint(st.session_state.game)
        st.rerun()
    with st.expander("Continue from a save"):
        uploaded = st.file_uploader("Saved simulation (.json)", type="json", key="setup_upload")
        if st.button("Continue simulation", disabled=uploaded is None):
            try:
                set_game(loads(uploaded.getvalue(), allow_invalid_drafts=True))
                checkpoint(st.session_state.game)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def show_forecast(game, faction):
    st.markdown("**Expected after this turn**")
    try:
        forecast = cached_forecast(dumps(game))["factions"][faction]
    except (InvalidOrder, ValueError) as exc:
        st.warning(f"Forecast unavailable until orders are valid: {exc}")
        return
    rows = forecast["resources"]
    for row, col in zip(rows[:5], st.columns(5)):
        col.metric(row["resource"], f"{row['expected']:,.2f}", delta=f"{row['change']:+,.2f}")
    if game.mode == "solo":
        st.caption("Includes current choices and projected computer responses. Values use the same calculation as End year; previewing does not advance the game.")
    else:
        st.caption("Based on all factions' current drafts. Other players may still change their orders before resolution.")
    with st.expander("Resource forecast breakdown"):
        st.dataframe([{"Resource": r["resource"], "Now": round(r["current"], 3), "After orders & transfers": round(r["after_orders"], 3), "Annual system change": round(r["system_change"], 3), "Expected balance": round(r["expected"], 3), "Net change": round(r["change"], 3)} for r in rows], hide_index=True, width="stretch")
        st.caption("Currency, energy, minerals, innovation, and military are stocks. Compute and productivity reset annually: their forecast is next year's available capacity, not banked unused points. Military includes production, recovery, and combat losses.")
        st.dataframe([{"Cash-flow item": name.replace("_", " ").capitalize(), "Expected T USD": round(value, 4)} for name, value in forecast["ledger"].items()], hide_index=True, width="stretch")
        production = forecast["production"]
        if min(production.get("energy_supply", 1), production.get("compute_supply", 1), production.get("thermal_supply", 1)) < 1 - 1e-8:
            st.warning(f"Expected shortages: energy operation {production['energy_supply']:.0%}, compute operation {production['compute_supply']:.0%}, thermal operation {production['thermal_supply']:.0%}.")
        if forecast["ledger"].get("new_borrowing", 0) > 0:
            st.warning(f"These orders are expected to require {forecast['ledger']['new_borrowing']:.3f} T of new domestic borrowing.")


def situation(game, f):
    n = game.nations[f]
    st.markdown('<div class="eyebrow">Global strategic picture</div>', unsafe_allow_html=True)
    st.title("Situation room")
    st.caption(f"{game.year} · Round {game.round} · {SCENARIO[f]['name']} · {n.government}")
    command_theater(game, f)
    with st.expander("National position"):
        metrics = st.columns(5)
        previous = game.history[-2]["nations"][f] if len(game.history) > 1 else None
        for col, label, field, value in zip(metrics, ["Treasury · T USD", "GDP · T USD", "Citizen content", "Military power", "Influence / 400"], ["currency", "gdp", "content", "military", "influence"], [n.currency, n.gdp, n.content, n.military, game.influence(f)]):
            delta = f"{value - previous[field]:+.2f}" if previous else None
            col.metric(label, f"{value:,.1f}", delta)
    met = sum(item["met"] for item in objective_progress(game, f))
    st.info(f"{OBJECTIVE_NAMES[f]} · {met}/{len(objective_progress(game, f))} conditions currently met · {game.objective_streaks[f]}/{game.rules.objective_hold_years} consecutive years secured. See Objectives for details.")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("Balance of power")
        data = [{"Faction": other, "GDP (T)": round(m.gdp, 2), "Debt (T)": round(game.debt(other), 2), "Content": round(m.content, 1), "Military": round(m.military, 1), "Influence": round(game.influence(other), 1)} for other, m in game.nations.items()]
        st.dataframe(data, hide_index=True, width="stretch")
        with st.expander("Infrastructure comparison"):
            st.dataframe([{"Faction": other, **{spec.name: game.nations[other].buildings[bid] for bid, spec in BUILDINGS.items()}} for other in FACTIONS], hide_index=True, width="stretch")
        st.caption("All information is public. The world map is schematic; fronts represent abstract theaters, not national borders.")
    with right:
        st.subheader("Command briefing")
        if game.reports:
            messages = game.reports[-1]["messages"]
            relevant = [m for m in messages if f in m or any(front in m for front in FRONTS)]
            for message in relevant[-6:]:
                st.write(f"• {message}")
        else:
            st.write(SCENARIO[f]["brief"])
            st.info("Start in Economy & construction. Allocate some productivity, then visit Military fronts to deploy forces. Nothing advances until you end the year.")
        if n.transition_target:
            st.warning(f"Government transition: {n.transition_remaining} years remaining. Civil unrest applies each year.")
        if n.last_ledger.get("new_borrowing", 0) > 0:
            st.warning("Your last budget required new borrowing. Review taxes and upkeep in Government & debt.")
        for trait in TRAITS[f]:
            st.caption(trait)


def economy(game, f):
    n, o = game.nations[f], game.orders[f]
    st.title("Economy & construction")
    st.markdown("**Plan now → Build & produce at End year → Spend or deploy next turn.**")
    st.info("Assigning productivity drafts construction; nothing is built immediately. At End year, completed facilities enter that year's production cycle and pay upkeep; shortages can limit output. Unfinished work carries over, but needs more productivity assigned in a later year to finish.")
    columns = st.columns(5)
    for col, label, value in zip(columns, ["Treasury · T USD", "Energy · PJ", "Minerals · tonnes", "Available compute · units", "Productivity · points"], [n.currency, n.energy, n.minerals, n.compute, n.productivity]):
        col.metric(label, f"{value:,.1f}")
    st.caption("Compute uses abstract FLOP-capacity units: the source gives +10 per data center without defining a physical scale.")
    construction_slot = st.container(key="construction_status")
    forecast_slot = st.container()
    card_slots = {}
    for is_project, catalog, label in ((False, BUILDINGS, "Facilities"), (True, PROJECTS, "Projects")):
        st.subheader(label)
        for row in range(0, len(catalog), 2):
            for col, (bid, spec) in zip(st.columns(2), list(catalog.items())[row:row + 2]):
                with col.container(border=True, key=f"investment_card_{bid}"):
                    st.markdown(f"**{spec.name}**" + (f" · {n.buildings[bid]} completed now" if not is_project else " · repeatable project"))
                    st.caption(spec.description)
                    cost = investment_cost(game, f, bid)
                    parts = [f"{cost['currency']:.3f} T", f"{cost['minerals']:.2f} minerals"]
                    if cost["compute"]:
                        parts.append(f"{cost['compute']:g} compute")
                    if cost["energy"]:
                        parts.append(f"{cost['energy']:g} energy")
                    st.caption(f"Work per unit: {cost['productivity']:g} productivity · Startup resources: " + " · ".join(parts))
                    if bid in n.progress:
                        st.progress(n.progress[bid], text=f"Saved from previous years: {work_percent(n.progress[bid])}; startup resources already paid")
                    points = st.number_input(f"Productivity → {spec.name}", min_value=0.0, max_value=max(0.0, float(n.productivity)), value=float(o.investments.get(bid, 0)), step=1.0, key=key(game, f, bid), disabled=f in game.submitted,
                        help="This is work in productivity points, not a building count. Press Enter or leave the field to update the preview. Orders build at End year. Assign enough work to finish one or more units; any unfinished unit carries over and needs a new allocation next year.")
                    if points > 0:
                        o.investments[bid] = points
                    else:
                        o.investments.pop(bid, None)
                    card_slots[bid] = (st.container(), cost["productivity"])
    used = sum(o.investments.values())
    st.progress(min(1.0, used / max(n.productivity, .01)), text=f"{used:.1f} / {n.productivity:.1f} productivity allocated")
    st.caption("Unallocated productivity expires. Each new unit charges its full startup resource costs at End year, even if it only partly completes. Work already paid for is not charged again. Investments resolve in the order listed above.")
    st.caption("Unit prices reflect active trade agreements. The resource forecast also applies projected new agreements and their discounts.")
    # Match the visibly documented order, independently of click sequence.
    o.investments = {bid: o.investments[bid] for bid in INVESTMENTS if bid in o.investments}
    # Fill previews only after every widget has updated the shared draft.
    forecast, error = projection(game)
    rows = forecast["factions"][f]["construction"] if forecast else construction_rows(game, f)
    with construction_slot:
        construction_overview(game, f, rows, error)
    for row in rows:
        slot, current_work_cost = card_slots[row["key"]]
        with slot:
            construction_card(row, game.year, current_work_cost)
    with st.expander("Last production report & operating costs"):
        if n.last_production:
            st.dataframe([{"Metric": k.replace("_", " ").capitalize(), "Value": round(v, 3)} for k, v in n.last_production.items()], hide_index=True, width="stretch")
        else:
            st.caption("The first report appears after you end a year.")
        st.dataframe([{"Facility": spec.name, "Currency upkeep (T)": spec.currency_upkeep, "Energy": spec.energy_upkeep, "Compute": spec.compute_upkeep, "Minerals": spec.mineral_upkeep} for spec in BUILDINGS.values()], hide_index=True, width="stretch")
    with forecast_slot:
        show_forecast(game, f)


def diplomacy(game, f):
    n, o = game.nations[f], game.orders[f]
    st.title("Diplomacy")
    st.caption("Trade and alliances require matching offers from both factions. Either partner can withdraw. In solo play, computer opponents consider relations when responding.")
    for other, col in zip((x for x in FACTIONS if x != f), st.columns(3)):
        with col.container(border=True):
            st.subheader(SCENARIO[other]["name"])
            st.metric("Relationship", f"{n.relations[other]:.2f} / 5")
            st.caption(f"Their tariff on you: {game.nations[other].tariffs[f]:.0%}")
            o.tariffs[other] = st.slider(f"Tariff on {other} (%)", 0, 50, int(round(o.tariffs.get(other, 0) * 100)), key=key(game, f, f"tariff_{other}"), disabled=f in game.submitted) / 100
            for field, label in (("trade_offers", "Offer / maintain trade"), ("alliance_offers", "Offer / maintain alliance"), ("share_bonus", "Share my trade benefit"), ("improve_relations", f"Diplomatic outreach · {game.rules.diplomacy_cost:.2f} T"), ("foreign_aid", f"Send foreign aid · {game.rules.foreign_aid_amount:.1f} T")):
                if field == "share_bonus" and f not in ("US", "China"):
                    continue
                checked = st.checkbox(label, value=other in getattr(o, field), key=key(game, f, f"{field}_{other}"), disabled=f in game.submitted)
                values = getattr(o, field)
                if checked and other not in values:
                    values.append(other)
                elif not checked and other in values:
                    values.remove(other)
            active = []
            if pair(f, other) in game.trades:
                active.append("Trade agreement")
            if pair(f, other) in game.alliances:
                active.append("Military alliance")
            st.caption("Active: " + (" · ".join(active) if active else "No agreements"))
            pending = game.orders[other]
            st.caption("Their current offers: " + ", ".join(label for label, values in (("trade", pending.trade_offers), ("alliance", pending.alliance_offers)) if f in values) if f in pending.trade_offers or f in pending.alliance_offers else "No offer currently recorded from this faction.")
    st.info("EU trade shares a 25% data-center cost discount automatically. The US can share a 20% compute-consumption discount; China can share a 20% productivity increase. Bonuses do not stack with a faction's own copy.")
    st.caption("Tariffs earn some revenue but suppress trade and damage relations. Relationships also deteriorate slightly each year unless cooperation offsets the drift.")
    st.caption(f"Foreign aid transfers treasury to the recipient and improves relations by {game.rules.foreign_aid_relation_gain:g} / 5, before the US diplomatic modifier. Incoming aid cannot fund orders in the same year.")


def military(game, f):
    n, o = game.nations[f], game.orders[f]
    st.title("Military fronts")
    st.caption("Deployment persists between years. Reserves avoid combat losses. Unopposed forces establish influence; opposing coalitions inflict simultaneous attrition.")
    a, b, c = st.columns(3)
    a.metric("Total military power", f"{n.military:.1f}")
    b.metric("Currently deployed", f"{sum(n.deployments.values()):.1f}")
    c.metric("Established influence", f"{game.influence(f):.1f} / 400")
    st.caption(f"Current military capacity: {n.military_capacity:.1f}. Reserve recovery restores up to {game.rules.reserve_recovery:.0%} of capacity per year when reserves are present. Current dominance tax bonus: {dominance_bonus(game, f):.0%}.")
    command_theater(game, f)
    reserve = n.military - sum(o.deployments.values())
    if reserve >= 0:
        st.success(f"Planned reserve: {reserve:.1f} military power.")
    else:
        st.error(f"Overcommitted by {-reserve:.1f} points. Reduce allocations before ending the year.")
    with st.expander("How combat works"):
        st.write(f"Each coalition's annual loss is max(0, {game.rules.combat_base_decay:.0%} of its strength + {game.rules.combat_attrition:.0%} of the difference between the strongest opposing coalition and its own strength), capped at deployed strength. Losses are shared in proportion to deployment. All calculations use the same pre-combat snapshot.")
        st.write(f"A coalition containing Russia takes 10% less damage. Connected allies present in the same front form a coalition. If only one coalition remains, it gains {game.rules.influence_gain:g} influence, split by surviving strength.")
        st.write("Each front holds at most 100 influence. Once unclaimed influence runs out, new control displaces rival influence proportionally. Contested fronts grant no influence while more than one coalition survives. Influence already established remains after withdrawal.")
        st.write("Military shares of at least 25%, 50%, and 75% provide tax bonuses of 5%, 10%, and 15% respectively per front. These use each faction's own deployment after orders and before combat; allied strength is not double-counted. Bonuses add across fronts.")


def government(game, f):
    n, o = game.nations[f], game.orders[f]
    st.title("Government & debt")
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Domestic policy")
        o.tax_rate = st.slider("Tax revenue as a share of GDP (%)", 0.0, 75.0, float(o.tax_rate * 100), .1, key=key(game, f, "tax"), disabled=f in game.submitted) / 100
        st.caption(f"At current GDP, this raises {n.gdp * o.tax_rate:.3f} T per year before other income and costs.")
        o.government = st.selectbox("Government type", GOVERNMENTS, index=GOVERNMENTS.index(o.government), key=key(game, f, "government"), disabled=bool(n.transition_target) or f in game.submitted)
        if n.transition_target:
            st.warning(f"Transition to {n.transition_target}: {n.transition_remaining} years remaining. Annual unrest: {game.rules.transition_unrest:g} content before national modifiers.")
        elif o.government != n.government:
            st.warning(f"This begins a {game.rules.government_transition_years}-year transition. The current government's effects continue until completion; the transition cannot be redirected midway.")
        effect = GOVERNMENT_EFFECTS[o.government]
        st.caption(f"Government effects when active: ×{effect['productivity']:.2f} productivity · ×{effect['innovation']:.2f} innovation · {effect['content']:+g} content adjustment.")
        st.metric("Citizen content", f"{n.content:.1f} / 100")
        st.caption("High taxes, active conflict, shortages, and transitions increase discontent. Innovation, GDP growth, and public services can improve it. Lower content increases domestic interest rates.")
    with right:
        st.subheader("Public finances")
        st.metric("Total outstanding debt · T USD", f"{game.debt(f):.3f}")
        st.write(f"Domestic debt: **{n.domestic_debt:.3f} T** at **{domestic_interest(game, f):.2%}**")
        o.domestic_repayment = st.number_input("Repay domestic principal (T)", 0.0, float(n.domestic_debt), float(o.domestic_repayment), step=.1, key=key(game, f, "repay_domestic"), disabled=f in game.submitted)
        st.caption("Operating shortfalls automatically become domestic debt. New discretionary spending must fit your current treasury.")
        if n.last_ledger:
            with st.expander("Last year's complete cash ledger", expanded=True):
                st.dataframe([{"Item": k.replace("_", " ").capitalize(), "T USD": round(v, 4)} for k, v in n.last_ledger.items()], hide_index=True, width="stretch")
    st.subheader("Foreign debt contracts")
    st.caption("Rates are set by the lender at maturity. Borrowers may repay principal at maturity; unpaid principal rolls into a new fixed-term contract. Higher renewal rates harm bilateral relations.")
    for c in game.contracts:
        if f not in (c.borrower, c.lender) or c.principal < 1e-8:
            continue
        mature = game.round >= c.matures_round
        with st.expander(f"{c.borrower} owes {c.lender} · {c.principal:.3f} T · {c.rate:.1%} · " + ("RENEWAL OPEN" if mature else f"locked until {game.rules.start_year + c.matures_round - 1}")):
            st.write(f"Annual interest transfer: **{c.principal * c.rate:.4f} T** from {c.borrower} to {c.lender}.")
            if f == c.lender:
                rate = st.number_input(f"Renewal interest rate (%) · {c.id}", 0.0, 20.0, float(o.contract_rates.get(c.id, c.rate) * 100), .25, key=key(game, f, f"rate_{c.id}"), disabled=not mature or f in game.submitted)
                if mature:
                    o.contract_rates[c.id] = rate / 100
            if f == c.borrower:
                amount = st.number_input(f"Repay foreign principal (T) · {c.id}", 0.0, float(c.principal), float(o.foreign_repayments.get(c.id, 0)), .1, key=key(game, f, f"repay_{c.id}"), disabled=not mature or f in game.submitted)
                if mature:
                    o.foreign_repayments[c.id] = amount


def chronicle(game, f):
    st.title("Chronicle")
    st.caption("A record of decisions, economic outcomes, and changes in the balance of power.")
    metric = st.selectbox("Compare factions", ["gdp", "currency", "debt", "content", "innovation", "military", "influence", "energy", "minerals"], format_func=lambda v: v.replace("_", " ").title())
    frame = pd.DataFrame([{ "Year": row["year"], **{other: row["nations"][other][metric] for other in FACTIONS}} for row in game.history]).set_index("Year")
    st.line_chart(frame, color=[COLORS[other] for other in FACTIONS])
    if not game.reports:
        st.info("End your first year to begin the chronicle.")
    for report in reversed(game.reports):
        with st.expander(f"{report['year']} · Round {report['round']} · {len(report['messages'])} developments", expanded=report == game.reports[-1]):
            for message in report["messages"]:
                st.write(f"• {message}")


def objectives(game, f):
    st.title("Strategic objectives")
    st.caption(f"Victory mode: {game.rules.victory_mode}. Conditions are checked after each completed round. A failed condition resets that faction's consecutive-year count.")
    selected = st.selectbox("Inspect faction objectives", FACTIONS, index=FACTIONS.index(f), key=key(game, f, "inspect_objectives"))
    st.subheader(OBJECTIVE_NAMES[selected])
    objective_dashboard(game, selected)


def reference(game, f):
    st.title("Rules & reference")
    st.write("The consolidated design below defines the game's rules, starting scenario, and objectives.")
    tabs = st.tabs(["Game design", "Current balance settings"])
    with tabs[0]:
        design = (REPOSITORY / "DESIGN.md").read_text()
        st.download_button("Download game design", design, "DESIGN.md", "text/markdown", key="download_design")
        st.markdown(design)
    with tabs[1]:
        st.json(asdict(game.rules))


def footer(game, f):
    st.divider()
    if st.session_state.get("page") != "Economy & construction":
        show_forecast(game, f)
    decision_briefing(game, f)
    order, nation = game.orders[f], game.nations[f]
    left, right = st.columns([2, 1], gap="large")
    error = None
    with left:
        st.markdown("**Current orders**")
        st.caption(f"Productivity: {sum(order.investments.values()):.1f} / {nation.productivity:.1f} · Military committed: {sum(order.deployments.values()):.1f} / {nation.military:.1f}")
        try:
            preview = preview_plan(game, f)
            st.caption(f"Own draft spending: {preview['spending']:.3f} T. The forecast above includes incoming transfers, annual income, and upkeep.")
        except InvalidOrder as exc:
            error = str(exc)
            st.error(error)
    with right:
        label = "Commit orders & pass turn" if game.mode == "hotseat" and len(game.submitted) < 3 else "End year · resolve all factions"
        if st.button(label, type="primary", width="stretch", disabled=error is not None or f in game.submitted, key="end_year"):
            try:
                result = st.session_state.game_session.commit(f)
            except (InvalidOrder, ValueError) as exc:
                st.error(str(exc))
                st.caption("Revise the named faction's plan. In hotseat, select that faction and reopen its orders.")
            else:
                sync_session()
                if result.resolved:
                    st.session_state.review_open = True
                    st.session_state.review_step = 0
                cue("victory" if result.new_victory else "resolve" if result.resolved else "commit")
                if game.mode == "hotseat":
                    st.session_state.commander = result.next_commander
                    st.session_state.handoff = True
                checkpoint(st.session_state.game)
                st.rerun()
    if game.mode == "solo":
        st.caption("Computer factions submit their orders when you end the year. They follow the same resource and combat rules.")
    elif game.mode == "sandbox":
        st.caption("Switch commanders in the sidebar to edit other factions. End year resolves all four drafts together.")


def main():
    if not st.session_state.get("recovery_checked"):
        st.session_state.recovery_checked = True
        restore_checkpoint()
    audio_slot = settings_controls()
    apply_display()
    if "game" not in st.session_state:
        if st.session_state.get("intro_seen"):
            setup()
        else:
            intro_screen()
        render_audio(audio_slot)
        return
    if "game_session" not in st.session_state:
        set_game(st.session_state.game)
    sync_session()
    game = st.session_state.game
    if st.session_state.get("show_opening_briefing"):
        # Keep the navigation widget's value while its command desk is hidden.
        if "page" in st.session_state:
            st.session_state.page = st.session_state.page
        intro_screen(resuming=True)
        render_audio(audio_slot)
        return
    with st.sidebar:
        st.markdown('<div class="eyebrow">Strategic command</div>', unsafe_allow_html=True)
        st.title("WW3")
        st.caption(f"YEAR {game.year} · ROUND {game.round}")
        if st.button("View opening briefing", key="view_opening_briefing", width="stretch"):
            st.session_state.show_opening_briefing = True
            st.rerun()
        if game.mode == "solo":
            f = game.player
            st.markdown(f"**{SCENARIO[f]['name']}**")
            st.caption("Single player · 3 computer opponents")
        else:
            f = st.selectbox("Command faction", FACTIONS, index=FACTIONS.index(st.session_state.commander), key=f"commander_{st.session_state.epoch}_{game.round}_{len(game.submitted)}")
            st.session_state.commander = f
            st.caption("Local hotseat" if game.mode == "hotseat" else "Sandbox · all factions under your control")
        page = st.radio("Command desk", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        st.caption("ORDERS STATUS")
        for other in FACTIONS:
            status = "Committed" if other in game.submitted else "Computer" if game.mode == "solo" and other != f else "Planning"
            st.caption(f"{other} · {status}")
        if f in game.submitted and st.button("Reopen this faction's orders"):
            st.session_state.game_session.reopen(f)
            sync_session()
            st.session_state.handoff = False
            checkpoint(st.session_state.game)
            st.rerun()
    if st.session_state.get("handoff"):
        st.title(f"Pass command to {SCENARIO[f]['name']}")
        st.write(f"{len(game.submitted)} of 4 factions have committed orders for {game.year}.")
        st.caption("Hotseat uses shared information. Every faction plans before the world advances.")
        if st.button("Open command desk", type="primary"):
            st.session_state.handoff = False
            checkpoint(game)
            st.rerun()
    else:
        if game.winners:
            st.success(f"Victory secured by {' + '.join(game.winners)}. You can keep playing this simulation or start a new campaign.")
        summary_slot = st.container(key="planning_summary")
        turn_review(game, f)
        {PAGES[0]: situation, PAGES[1]: economy, PAGES[2]: diplomacy, PAGES[3]: military, PAGES[4]: government, PAGES[5]: objectives, PAGES[6]: chronicle, PAGES[7]: reference}[page](game, f)
        if f not in game.submitted and st.session_state.game_session.replace_order(f, game.orders[f]):
            st.session_state.draft_history = st.session_state.game_session.draft_history
            cue("warning" if projection(game)[1] else "order")
        with summary_slot:
            planning_summary(game, f, lambda: undo_draft(game, f), lambda: reset_draft(game, f))
        guided_opening(game, f)
        draft_comparison(game, f, lambda: remember_draft(game, f), lambda: restore_remembered(game, f))
        footer(game, f)
    render_audio(audio_slot)
    checkpoint(game)
    save_controls(game)
    with st.sidebar.expander("New simulation"):
        st.caption("The local recovery slot follows your next campaign. Download a portable copy to keep this one separately.")
        if st.button("Return to scenario setup", width="stretch"):
            recovery = st.session_state.recovery_session
            preferences = {name: st.session_state.get(name, default) for name, default in PRESENTATION_DEFAULTS.items()}
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state.recovery_checked = True
            st.session_state.recovery_session = recovery
            st.session_state.update(preferences)
            st.session_state.intro_seen = True
            st.rerun()


if __name__ == "__main__":
    main()
