"""Player-facing construction progress and annual completion previews."""

from collections import Counter

import streamlit as st

from ww3.core.engine import EPS
from ww3.core.rules import INVESTMENTS


def work_percent(progress):
    # An unfinished unit must never look complete because of display rounding.
    return f"{min(99.9, progress * 100):.1f}%" if 0 < progress < 1 else f"{progress:.0%}"


def construction_overview(game, faction, rows, error):
    st.subheader("Construction status")
    if game.reports:
        messages = Counter(game.reports[-1]["messages"])
        finished = [f"{spec.name} ×{messages[f'{faction} completed {spec.name.lower()}.']}"
                    for spec in INVESTMENTS.values()
                    if messages[f"{faction} completed {spec.name.lower()}."]]
        if finished:
            st.success("Completed last year: " + " · ".join(finished))
    active = [r for r in rows if r["current_progress"] > 0 or r["allocated_work"] > 0]
    if error:
        st.warning(f"Completion preview unavailable until orders are valid: {error}")
    if not active:
        st.caption("No unfinished work or construction orders. Assign productivity below to draft a build.")
        return
    table = []
    for row in active:
        outcome = "Unavailable"
        if row["forecast_valid"]:
            if row["allocated_work"] <= EPS:
                outcome = "Paused · no work assigned"
            else:
                outcome = f"{row['completed']} complete"
                if row["expected_progress"]:
                    unit = "next unit" if row["completed"] else "unfinished unit"
                    outcome += f" · {work_percent(row['expected_progress'])} of {unit}"
        table.append({
            "Investment": row["name"],
            "Completed now": str(row["current_count"]) if row["kind"] == "building" else "Repeatable project",
            "Saved progress": work_percent(row["current_progress"]),
            "Work this year": f"{row['allocated_work']:g}",
            "Expected at End year": outcome,
            "Work left for later": f"{row['expected_remaining_work']:g}" if row["forecast_valid"] else "—",
        })
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption("Work is measured in productivity points. Saved progress is already built; the End year columns preview your draft. Increase this year's allocation to finish sooner, or assign more work in a later year. Remaining work uses projected trade discounts.")
    if game.mode != "solo":
        st.caption("Expected completions use all current drafts and may change if another player changes a trade offer.")


def construction_card(row, year, current_work_cost):
    """Render after every investment widget has synchronized the draft."""
    active = row["current_progress"] > 0 or row["allocated_work"] > 0
    if row["forecast_valid"] and abs(row["work_per_unit"] - current_work_cost) > EPS:
        st.caption(f"With projected trade agreements: {row['work_per_unit']:g} productivity per unit.")
    if not active:
        st.caption(f"Assign {row['remaining_work']:g} productivity to finish one unit at End year.")
        return
    if row["current_progress"] > 0 and row["allocated_work"] <= EPS:
        st.warning("Paused — no productivity assigned this year.")
        st.caption(f"Assign {row['remaining_work']:g} productivity to finish this unit. Saved work stays; construction does not advance automatically.")
    if not row["forecast_valid"]:
        st.caption("Completion preview unavailable until orders are valid. Saved progress is unchanged.")
        return
    if row["allocated_work"] <= EPS:
        return
    if row["completed"]:
        noun = "facility" if row["kind"] == "building" else "project"
        plural = "facilities" if row["kind"] == "building" else "projects"
        st.success(f"At End year: {row['completed']} {noun if row['completed'] == 1 else plural} completed.")
        if row["kind"] == "building":
            st.caption(f"Completed facilities: {row['current_count']} now → {row['expected_count']} next turn. New facilities produce and pay upkeep at End year; remaining output is available for your {year + 1} orders. Shortages can limit production.")
        else:
            st.caption(f"Project benefits apply at End year and appear in your {year + 1} resources and capacity.")
    else:
        st.markdown("**At End year: no completion yet.**")
    if row["expected_progress"]:
        unit = "next unit" if row["completed"] else "unfinished unit"
        st.progress(row["expected_progress"], text=f"After End year: {work_percent(row['expected_progress'])} of {unit}")
        st.caption(f"With this draft, {row['expected_remaining_work']:g} productivity remains at the projected work cost. Add more now or continue in a later year. This unfinished unit gives no output or benefit yet.")
    elif row["completed"]:
        st.progress(1.0, text="After End year: all assigned work completes · nothing left unfinished")
    if row["started"]:
        st.caption(f"Starts {row['started']} new {'unit' if row['started'] == 1 else 'units'}: full startup resource costs are charged at End year, including any unfinished unit.")
    else:
        st.caption("Finishes or advances already-paid work; no new startup resource costs.")
