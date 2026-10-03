"""Command-map, draft summary, guidance and recorded turn review."""

from html import escape
from dataclasses import asdict

import streamlit as st

from .catalog import FACTIONS, FRONTS
from .briefing import objective_briefing, resource_alerts, victory_watch
from .components import command_map
from .engine import InvalidOrder
from .forecast import forecast_round
from .map_view import render_map
from .persistence import dumps, loads
from .planning import changed_decisions, compare_draft
from .models import Order
from .reporting import PHASES, message_phase, phase_messages
from .strategy import objective_progress, theater_snapshot


def key(game, faction, name):
    return f"{st.session_state.epoch}:{game.round}:{faction}:{name}"


@st.cache_data(show_spinner=False, max_entries=24)
def cached_forecast(payload):
    return forecast_round(loads(payload))


def projection(game):
    try:
        return cached_forecast(dumps(game)), None
    except (InvalidOrder, ValueError) as exc:
        return None, str(exc)


def command_theater(game, faction):
    n, order = game.nations[faction], game.orders[faction]
    st.subheader("Command map")
    selected = st.session_state.get("selected_front", FRONTS[0])
    result = command_map(data={"svg": render_map(game, selected, interactive=True)},
        key="command_map", on_select_change=lambda: None)
    if result.select in FRONTS and result.select != selected:
        st.session_state.selected_front = result.select
        st.session_state.front_selector = result.select
        st.rerun()
    st.session_state.setdefault("front_selector", selected)
    selected = st.selectbox("Inspect theater", FRONTS, key="front_selector", on_change=select_front)
    st.session_state.selected_front = selected
    st.caption("Select a map marker with a click, Tab + Enter, or the theater list. Pan horizontally on small screens. The map shows the resolved world; the panel compares your draft with its forecast.")
    with st.expander("Deployment orders · all four fronts", expanded=True):
        for name, col in zip(FRONTS, st.columns(4)):
            order.deployments[name] = col.number_input(f"Deploy power → {name}", 0.0, float(n.military),
                float(order.deployments[name]), step=5.0, key=key(game, faction, f"deploy_{name}"), disabled=faction in game.submitted)
        reserve = n.military - sum(order.deployments.values())
        st.caption(f"Planned reserve: {reserve:.1f} power · Deployment upkeep: {sum(order.deployments.values()) * game.rules.military_upkeep:.3f} T/year. Reserves avoid deployment upkeep and combat; they allow recovery up to military capacity.")
    current = theater_snapshot(game, selected)
    forecast, error = projection(game)
    future = forecast["fronts"][selected] if forecast else None
    st.markdown(f"### {selected}")
    st.caption(f"Current status: {current['status']}")
    own = current["factions"][faction]
    a, b, c = st.columns(3)
    a.metric("Your military share now", f"{own['share']:.1%}")
    b.metric("Your territorial influence", f"{own['influence']:.1f} / 100")
    c.metric("Your planned front upkeep", f"{order.deployments[selected] * game.rules.military_upkeep:.3f} T")
    st.caption("Military share measures troops present. Influence is established territorial control: withdrawal does not erase it, and contested fronts cannot gain it while multiple coalitions survive.")
    if error:
        st.warning(f"Fix the draft to see projected coalitions and outcomes: {error}")
    rows = []
    for f in FACTIONS:
        now = current["factions"][f]
        planned = future["planned"]["factions"][f] if future else None
        expected = future["expected"]["factions"][f] if future else None
        rows.append({"Faction": f, "Power now": round(now["deployed"], 2),
            "Planned power": round(planned["deployed"], 2) if planned else None,
            "Planned own share": f"{planned['share']:.1%}" if planned else "—",
            "Expected survivors": round(expected["deployed"], 2) if expected else None,
            "Expected own share": f"{expected['share']:.1%}" if expected else "—",
            "Influence now / 100": round(now["influence"], 2),
            "Expected influence / 100": round(expected["influence"], 2) if expected else None})
    st.dataframe(rows, hide_index=True, width="stretch")
    for label, groups in (("Current coalitions", current["coalitions"]),
            ("Planned coalitions before combat", future["planned"]["coalitions"] if future else None)):
        if groups is not None:
            st.write(f"**{label}:** " + (" · ".join(f"{' + '.join(g['members'])}: {g['strength']:.2f} power" for g in groups) or "No forces present"))
    if future:
        st.caption(f"Expected result: {future['expected']['status']}. Upkeep and tax bonuses use pre-combat deployments; objective checks use surviving forces.")
    with st.expander("Objectives affected by this theater", expanded=True):
        for f in FACTIONS:
            for index, item in enumerate(objective_progress(game, f)):
                if item["front"] != selected:
                    continue
                expected = forecast["objectives"][f][index] if forecast else None
                st.markdown(f"**{f} · {item['condition']}**")
                st.caption(f"Now: {item['current']} ({'met' if item['met'] else 'unmet'})"
                    + (f" → Expected: {expected['current']} ({'met' if expected['met'] else 'unmet'})" if expected else ""))
    st.caption("Forecast includes reproducible computer responses." if game.mode == "solo" else
        "Conditional forecast: other players can still edit uncommitted drafts, changing coalitions and outcomes.")


def planning_summary(game, faction, undo, reset):
    n, order = game.nations[faction], game.orders[faction]
    forecast, error = projection(game)
    changes = changed_decisions(game, faction)
    remaining = n.productivity - sum(order.investments.values())
    if st.session_state.get("text_scale", 100) >= 130:
        left = st.container()
        middle, right = st.columns(2)
    else:
        left, middle, right = st.columns([3.5, 1, 1.5])
    left.markdown(f"**{faction} · {remaining:.1f} productivity remaining · {len(changes)} changed decisions**")
    middle.button("Undo edit", key="undo_draft", disabled=faction in game.submitted or not st.session_state.draft_history.undo[faction], on_click=undo, width="stretch")
    right.button("Reset draft", key="clear_draft", disabled=faction in game.submitted, on_click=reset, width="stretch", help="Restore this faction's standing orders. You can undo the reset in this session.")
    labels = ["Treasury · T", "Energy · PJ", "Minerals · t", "Compute ↻", "Productivity ↻", "Innovation", "Military"]
    fields = ["currency", "energy", "minerals", "compute", "productivity", "innovation", "military"]
    rows = {r["key"]: r for r in forecast["factions"][faction]["resources"]} if forecast else {}
    table = '<div class="resource-scroll" role="region" aria-label="Planning resource balances" tabindex="0"><table class="resource-summary"><caption class="sr-only">Current resources, orders and transfers, annual changes and expected balances</caption><thead><tr><th>Planning ledger</th>'
    table += ''.join(f'<th scope="col">{escape(label)}</th>' for label in labels) + '</tr></thead><tbody>'
    for label, column in (("Current", "current"), ("Orders + transfers", "orders"), ("Annual change", "system_change"), ("Expected", "expected")):
        table += f'<tr><th scope="row">{label}</th>'
        for field in fields:
            row = rows.get(field)
            value = (row["after_orders"] - row["current"] if column == "orders" else row[column]) if row else getattr(n, field) if column == "current" else None
            formatted = "—" if value is None else (f"{value:+,.2f}" if column in ("orders", "system_change") else f"{value:,.2f}")
            table += f'<td>{formatted}</td>'
        table += '</tr>'
    st.markdown(table + '</tbody></table></div>', unsafe_allow_html=True)
    if error:
        st.error(f"Invalid draft — forecast cleared. {error}")
    else:
        spending = -forecast["factions"][faction]["ledger"]["planned_spending"]
        st.caption(f"Planned spending {spending:.3f} T · ↻ Compute and productivity renew each year; unused capacity expires. "
            + ("Includes computer responses." if game.mode == "solo" else "Other players can still change their drafts."))
    with st.sidebar.expander(f"Changed decisions · {len(changes)}", expanded=bool(changes)):
        for change in changes:
            st.write(change)
        if not changes:
            st.caption("No changes from standing orders. Reset restores deployments and policy to the resolved world; undo restores your previous edit.")


def navigate(page):
    st.session_state.page = page


def inspect_objective(front):
    st.session_state.selected_front = front
    st.session_state.front_selector = front
    navigate("Military fronts")


def objective_dashboard(game, faction):
    """Compare completed checks with exact, conditional post-combat checks."""
    forecast, error = projection(game)
    hold = game.objective_streaks[faction]
    required = game.rules.objective_hold_years
    st.progress(hold / required, text=f"{hold} / {required} consecutive completed years")
    if error:
        st.warning(f"Objective forecast unavailable until all drafts are valid: {error}")
    elif forecast:
        after = forecast["streaks"][faction]
        st.markdown(f"**Expected hold after combat: {after} / {required} years**")
        if hold and after == 0:
            st.warning("This draft is expected to reset the entire objective hold. Protect the conditions marked At risk below.")
        elif after > hold:
            st.success("This draft is expected to satisfy every condition for one more completed year.")
        elif not after:
            st.info("The hold cannot begin until every condition is met in the same post-combat check.")
    st.caption("Now is the resolved world. Expected values include this year's orders, alliances and combat; they do not advance the campaign. Gaps describe the resulting position, not a number of troops to deploy.")
    for index, item in enumerate(objective_briefing(game, faction, forecast)):
        current, expected = item["current"], item["expected"]
        with st.container(border=True):
            st.markdown(f"**{current['condition']}**")
            now, future = st.columns(2)
            now.markdown(f"**Now · {'Met' if current['met'] else 'Unmet'}**  \n{current['current']}")
            future.markdown(f"**After combat · {item['change']}**  \n" + (expected["current"] if expected else "No valid forecast"))
            st.caption(current["detail"])
            if not (expected if expected is not None else current)["met"]:
                st.write(f"{'Expected gap' if expected else 'Current gap'}: {item['gap']}")
                if item["blocker"]:
                    st.warning(item["blocker"])
                st.caption(item["advice"])
            st.button(f"Inspect {current['front']}", key=f"objective_front_{faction}_{index}",
                on_click=inspect_objective, args=(current["front"],))
    st.subheader("Victory watch")
    mode = game.rules.victory_mode
    if mode == "open":
        st.info("Objectives are tracked for reference. Open-ended mode never declares a winner.")
    elif mode == "influence":
        st.info(f"Victory goes to the highest total territorial influence once it reaches {game.rules.victory_target:g}. Tied leaders share victory; objective holds are reference only.")
    metric = "Influence" if mode == "influence" else "Hold years"
    rows = []
    for item in victory_watch(game, forecast):
        rows.append({"Faction": item["faction"], "Conditions now": f"{item['conditions_now']}/{item['condition_count']}",
            "Conditions expected": f"{item['conditions_expected']}/{item['condition_count']}" if forecast else "—",
            f"{metric} now": item["current"], f"{metric} expected": item["expected"], "Target": item["target"],
            "Outlook": "Victory secured" if item["secured"] else "Victory this year" if item["wins_this_year"] else
                "Reference only" if mode == "open" else "Continue planning"})
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Forecast includes reproducible computer responses." if game.mode == "solo" else
        "Conditional on every faction's current draft. Other players may revise uncommitted orders.")


def decision_briefing(game, faction):
    """Place consequences beside the commit control, on every command screen."""
    forecast, error = projection(game)
    if error:
        st.caption("Objective and victory projections are unavailable while a draft is invalid.")
        return
    if game.rules.victory_mode != "influence":
        expected = forecast["streaks"][faction]
        hold = game.objective_streaks[faction]
        conditions = forecast["objectives"][faction]
        met = sum(item["met"] for item in conditions)
        label = "Objective reference" if game.rules.victory_mode == "open" else "Objective outlook"
        st.markdown(f"**{label}: {met}/{len(conditions)} expected conditions · hold {hold} → {expected}/{game.rules.objective_hold_years} years**")
        if hold and expected == 0:
            failed = [item["condition"] for item in conditions if not item["met"]]
            st.warning("Expected hold reset: " + "; ".join(failed) + ".")
    else:
        own = next(item for item in victory_watch(game, forecast) if item["faction"] == faction)
        st.markdown(f"**Influence outlook: {own['current']:.1f} → {own['expected']:.1f} / {own['target']:g}**")
    imminent = [item["faction"] for item in victory_watch(game, forecast) if item["wins_this_year"]]
    if imminent:
        message = f"Expected victory this year: {' + '.join(imminent)}. Review the objective and theater forecast before resolving."
        (st.success if imminent == [faction] else st.warning)(message)
    for level, text in resource_alerts(game, faction, forecast):
        getattr(st, level)(text)


@st.cache_data(show_spinner=False, max_entries=12)
def cached_comparison(payload, faction, remembered):
    return compare_draft(loads(payload, allow_invalid_drafts=True), faction, Order(**remembered))


def draft_comparison(game, faction, remember, restore):
    saved = st.session_state.draft_history.remembered.get(faction)
    with st.expander("Compare draft alternatives", expanded=saved is not None):
        st.caption("Remember a draft, then try another plan. Both forecasts use the current world and current rival drafts, including computer responses in solo. The remembered alternative lasts for this year and open session; restoring it is undoable.")
        a, b = st.columns(2)
        a.button("Remember this draft" if saved is None else "Replace remembered draft", key="remember_draft", disabled=faction in game.submitted, on_click=remember, width="stretch")
        b.button("Restore remembered draft", key="restore_remembered", disabled=saved is None or faction in game.submitted, on_click=restore, width="stretch")
        if saved is None:
            return
        comparison = cached_comparison(dumps(game), faction, asdict(saved))
        for name, result in comparison.items():
            if result["error"]:
                st.warning(f"{'This' if name == 'current' else 'Remembered'} draft has no valid forecast: {result['error']}")
        current, prior = (comparison[name]["forecast"] for name in ("current", "remembered"))
        if current and prior:
            st.dataframe([{"Resource": a["resource"], "This draft · expected": round(a["expected"], 3),
                "Remembered · expected": round(b["expected"], 3), "This minus remembered": round(a["expected"] - b["expected"], 3)}
                for a, b in zip(current["factions"][faction]["resources"], prior["factions"][faction]["resources"])], hide_index=True, width="stretch")
            st.dataframe([{"Theater": name,
                "This draft · own share": f"{current['fronts'][name]['expected']['factions'][faction]['share']:.1%}",
                "Remembered · own share": f"{prior['fronts'][name]['expected']['factions'][faction]['share']:.1%}",
                "This draft · influence": round(current['fronts'][name]['expected']['factions'][faction]['influence'], 2),
                "Remembered · influence": round(prior['fronts'][name]['expected']['factions'][faction]['influence'], 2)} for name in FRONTS], hide_index=True, width="stretch")
            st.write(f"Expected objective hold: this draft **{current['streaks'][faction]}**, remembered **{prior['streaks'][faction]}** / {game.rules.objective_hold_years} years.")
        st.caption("Positive differences mean larger values, not necessarily a better plan: debt, unused capacity and exposed forces need context.")


def select_front():
    st.session_state.selected_front = st.session_state.front_selector


def toggle_guidance():
    st.session_state.guide_enabled = st.session_state.guide_choice


def guided_opening(game, faction):
    with st.sidebar.expander("First three years", expanded=game.round <= 3):
        st.session_state.setdefault("guide_choice", st.session_state.get("guide_enabled", True))
        enabled = st.checkbox("Show opening guidance", key="guide_choice", on_change=toggle_guidance)
        if not enabled:
            st.caption("Guidance skipped. You can turn it on again here.")
            return
        if game.round > 3:
            st.write("The introduction is complete. Your campaign continues with the same objective rules.")
            return
        st.markdown(f"**Year {game.round} of 3 · Your orders stay yours**")
        if game.round == 1:
            st.write("The EU has economic strength, fewer forces in Eastern Europe and an Arctic balance to protect." if faction == "EU" else
                "Compare your strongest front with the conditions required by your faction's objectives.")
            st.write("Try one investment, consider a trade or alliance offer, and compare deployments. Keeping an existing policy is also a choice.")
        elif game.round == 2:
            st.write("Review what your first orders actually achieved. Compare the cost of another investment with defending your weakest objective.")
        else:
            st.write("Check whether your objective hold advanced or reset. A position must survive three consecutive resolved years under the default rules.")
        for label, page in (("1 · Choose an investment", "Economy & construction"), ("2 · Consider diplomacy", "Diplomacy"),
                ("3 · Compare deployments", "Military fronts"), ("4 · Inspect objective hold", "Objectives")):
            st.button(label, key=f"guide_{page}", on_click=navigate, args=(page,), width="stretch")
        order = game.orders[faction]
        st.caption(f"Your draft: {sum(order.investments.values()):.1f} productivity invested, {sum(order.deployments.values()):.1f} power deployed, "
            f"{len(order.trade_offers)} trade and {len(order.alliance_offers)} alliance offers. Agreements require matching offers.")
        st.write("Read the planning ledger: orders spend resources first; annual income, production and upkeep then produce the expected balance. Edit an order and compare it before ending the year.")
        st.caption(f"Actual objective hold: {game.objective_streaks[faction]}/{game.rules.objective_hold_years} years. Current military share and influence are different measures.")
        if game.reports:
            report = game.reports[-1]
            indices = report.get("highlights", {}).get(faction, [])
            if indices:
                st.write("Last year's actual result: " + report["messages"][indices[0]])


def review_step(step):
    st.session_state.review_step = step
    st.session_state.review_open = True


def close_review():
    st.session_state.review_open = False


def turn_review(game, faction):
    if not game.reports:
        return
    report = game.reports[-1]
    if not st.session_state.get("review_open", False):
        st.button(f"Replay {report['year']} results", key="replay_results", on_click=review_step, args=(0,))
        return
    with st.container(border=True):
        st.subheader(f"{report['year']} resolved · Turn review")
        st.button("Skip review / return to planning", key="skip_review", on_click=close_review)
        st.caption("Instant, manual steps in actual resolution order. Headlines rank objective-hold changes, shortages, borrowing and relative gains/losses; inspect each cause below.")
        for index in report.get("highlights", {}).get(faction, []):
            phase = message_phase(report, index)
            st.write(report["messages"][index].split(". ", 1)[0] + ".")
            st.button(f"Inspect cause · {PHASES[phase]}", key=f"cause_{index}", on_click=review_step, args=(list(PHASES).index(phase),))
        if "phase_ends" not in report:
            st.info("This older save has an ungrouped chronicle. New resolved turns include phase-by-phase explanations.")
            for message in report["messages"]:
                st.write(message)
        else:
            step = max(0, min(len(PHASES) - 1, st.session_state.get("review_step", 0)))
            phase = list(PHASES)[step]
            st.markdown(f"**{step + 1}/{len(PHASES)} · {PHASES[phase]}**")
            for message in phase_messages(report, phase):
                st.write(message)
            previous, following = st.columns(2)
            previous.button("Previous phase", disabled=step == 0, on_click=review_step, args=(step - 1,), width="stretch")
            following.button("Next phase", disabled=step == len(PHASES) - 1, on_click=review_step, args=(step + 1,), width="stretch")
            return
        st.button("Return to planning", on_click=close_review)
