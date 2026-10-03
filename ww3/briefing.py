"""Read-only decision support built from the engine's post-combat forecast."""

from .catalog import FACTIONS, FRONTS
from .strategy import EPS, objective_progress


OBJECTIVE_ADVICE = {
    "EU": (
        "Keep EU forces in Eastern Europe and strengthen their surviving coalition. Matching alliance offers can help; a coalition connected to Russia cannot qualify.",
        "Remove opposing coalitions, then hold Eastern Europe. New control first fills unclaimed influence and only then displaces rivals; a deployment advantage alone does not erase Russian influence.",
        "Balance the Arctic with surviving EU forces. Every other faction counts separately, including allies; concentrating allied power can break this ceiling.",
    ),
    "US": (
        "Clear every foreign force from South America. Allies count as foreign too, and coalition members do not fight one another.",
        "Concentrate surviving US forces in the Arctic. Allied power does not count toward your own military share.",
        "Keep enough surviving non-Chinese power in the Pacific to limit China's share. Withdrawing a counterweight can hand China the advantage.",
    ),
    "China": (
        "Concentrate surviving Chinese forces in the Pacific. The target is strict: merely reaching it is insufficient, and allied power does not count toward your share.",
        "Protect enough Chinese power in the Arctic while contesting the Pacific. Allied power does not count toward your own military share.",
    ),
    "Russia": (
        "Remove nearly all foreign military power from Eastern Europe. Allied forces still reduce Russia's own share.",
        "Keep sufficient surviving Russian power in the Arctic while contesting Eastern Europe. Allied power does not count toward your own share.",
    ),
}


def objective_gap(item):
    """Describe a measured gap without duplicating rule thresholds."""
    if item["met"]:
        return "Condition met at this check."
    gap = max(0.0, item["value"] - item["target"] if item["comparison"] == "<=" else item["target"] - item["value"])
    if item["comparison"] == ">" and gap == 0:
        return "Increase beyond the target; equality does not satisfy this strict condition."
    scaled = 100 * gap if item["unit"] == "share" else gap
    # A tiny surviving foreign force can block a zero-presence objective.
    # Never tell the player that an unmet condition needs a zero adjustment.
    number = f"{scaled:.3g}" if 0 < scaled < .05 else f"{scaled:.1f}"
    unit = "percentage points" if item["unit"] == "share" else item["unit"]
    amount = f"{number} {unit}"
    direction = "Reduce by" if item["comparison"] == "<=" else "Increase by"
    qualifier = "more than " if item["comparison"] == ">" else ""
    return f"{direction} {qualifier}{amount} to satisfy the condition."


def objective_briefing(game, faction, forecast=None):
    """Keep actual and forecast evidence distinct, including invalid drafts."""
    result = []
    for index, current in enumerate(objective_progress(game, faction)):
        expected = forecast["objectives"][faction][index] if forecast else None
        evaluated = expected if expected is not None else current
        change = "Forecast unavailable"
        if expected is not None:
            change = "Holding" if current["met"] and expected["met"] else "Newly met" if expected["met"] else "At risk" if current["met"] else "Still unmet"
        blocker = None
        if faction == "EU" and index == 1 and expected is not None and not expected["met"]:
            groups = forecast["fronts"][current["front"]]["expected"]["coalitions"]
            if len(groups) > 1:
                forces = "; ".join(f"{' + '.join(group['members'])}: {group['strength']:.1f} power" for group in groups)
                blocker = f"Still contested after combat ({forces}). No new influence is gained this year."
            elif not groups:
                blocker = "No forces survive to establish new control. Russian influence remains despite withdrawal."
            elif "Russia" in groups[0]["members"]:
                blocker = "Russia belongs to the surviving coalition, so its established influence is not displaced."
        result.append({"current": current, "expected": expected, "change": change,
            "gap": objective_gap(evaluated), "advice": OBJECTIVE_ADVICE[faction][index], "blocker": blocker})
    return result


def victory_watch(game, forecast=None):
    """List current/projected progress using the selected victory rules."""
    mode = game.rules.victory_mode
    projected = None
    if forecast is not None:
        projected = ({f: sum(forecast["fronts"][front]["expected"]["factions"][f]["influence"] for front in FRONTS)
            for f in FACTIONS} if mode == "influence" else forecast["streaks"])
    target = game.rules.victory_target if mode == "influence" else game.rules.objective_hold_years
    leaders = []
    if projected is not None and not game.winners and mode != "open":
        best = max(projected.values())
        leaders = [f for f in FACTIONS if (projected[f] >= target if mode == "objectives" else
            best >= target and abs(projected[f] - best) <= EPS)]
    return [{"faction": f, "current": game.influence(f) if mode == "influence" else game.objective_streaks[f],
        "expected": projected[f] if projected is not None else None, "target": target,
        "wins_this_year": f in leaders, "secured": f in game.winners,
        "conditions_now": sum(item["met"] for item in objective_progress(game, f)),
        "conditions_expected": sum(item["met"] for item in forecast["objectives"][f]) if forecast else None,
        "condition_count": len(objective_progress(game, f))} for f in FACTIONS]


def resource_alerts(game, faction, forecast):
    """Surface immediate consequences that otherwise hide in detailed ledgers."""
    if forecast is None:
        return []
    data = forecast["factions"][faction]
    alerts = []
    production = data["production"]
    shortages = [f"{label} at {production[name]:.0%}" for name, label in
        (("energy_supply", "energy operation"), ("compute_supply", "compute operation"), ("thermal_supply", "thermal operation"))
        if production.get(name, 1) < 1 - EPS]
    if shortages:
        alerts.append(("warning", "Expected shortages: " + ", ".join(shortages) + ". Review supply before adding dependent facilities."))
    borrowing = data["ledger"].get("new_borrowing", 0)
    operating = data["ledger"].get("operating_balance", 0)
    if borrowing > EPS:
        alerts.append(("warning", f"Expected new domestic borrowing: {borrowing:.3f} T; operating deficit: {max(0, -operating):.3f} T. Borrowing covers recurring bills; construction still requires cash. Review upkeep and taxes."))
    elif operating < -EPS:
        alerts.append(("warning", f"Expected operating deficit: {-operating:.3f} T, covered by your treasury this year. Review upkeep and taxes before reserves run out."))
    remaining = game.nations[faction].productivity - sum(game.orders[faction].investments.values())
    if remaining > EPS:
        alerts.append(("caption", f"{remaining:.1f} unallocated productivity expires at year end. Partial construction carries forward if you can afford to start it."))
    return alerts
