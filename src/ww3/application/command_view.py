"""Client-neutral command desk data. All predicted values come from the engine."""

from dataclasses import asdict
from functools import lru_cache
from math import isfinite

from ww3.application.briefing import objective_briefing, resource_alerts, victory_watch
from ww3.application.planning import changed_decisions
from ww3.core.catalog import COLORS, FACTIONS, FRONTS, GOVERNMENTS, SCENARIO, TRAITS
from ww3.core.construction import construction_rows
from ww3.core.engine import domestic_interest, investment_cost, new_game, preview_plan
from ww3.core.reporting import PHASES, message_phase, phase_messages
from ww3.core.rules import BUILDINGS, GOVERNMENT_EFFECTS, INVESTMENTS, Rules
from ww3.core.strategy import OBJECTIVE_NAMES, dominance_bonus, objective_progress, theater_snapshot
from ww3.persistence.preferences import DEFAULTS, valid_preferences

PAGES = ("Situation room", "Economy & construction", "Diplomacy", "Military fronts",
         "Government & debt", "Objectives", "Chronicle", "Rules & reference")

# The same scenario controls offered by the development client. Bounds are
# part of the command contract, rather than trusted client widget settings.
SCENARIO_FIELDS = {
    "combat_attrition": ("Combat strength-gap attrition", 0, .5, .01),
    "influence_gain": ("Influence per uncontested front", 1, 25, 1),
    "hostility_drift": ("Annual relationship deterioration", 0, .2, .01),
    "contract_years": ("Debt contract length · years", 1, 10, 1),
    "government_transition_years": ("Government transition · years", 1, 10, 1),
    "military_upkeep": ("Military upkeep · T per deployed point", 0, .02, .001),
    "objective_hold_years": ("Consecutive years for victory", 1, 10, 1),
    "ai_seed": ("Computer strategy seed", 0, 100000, 1),
    "victory_target": ("Total influence target", 150, 400, 10),
}
STARTING_FIELDS = {"starting_capital": ("Treasury · T", 1000),
                   "starting_energy": ("Energy · PJ", 1000),
                   "starting_minerals": ("Minerals · t", 1000),
                   "starting_content": ("Citizen content", 100)}
INTEGER_FIELDS = {"contract_years", "government_transition_years", "objective_hold_years", "ai_seed"}


def scenario_rules(values=None, seed=None):
    values = {} if values is None else values.copy() if isinstance(values, dict) else values
    if not isinstance(values, dict) or not set(values) <= SCENARIO_FIELDS.keys() | STARTING_FIELDS.keys() | {"victory_mode"}:
        raise ValueError("Unknown scenario setting.")
    if seed is not None:
        if "ai_seed" in values and seed != values["ai_seed"]:
            raise ValueError("Conflicting computer strategy seeds.")
        values["ai_seed"] = seed
    rules = Rules()
    for key, value in values.items():
        if key == "victory_mode":
            if value not in ("objectives", "open", "influence"):
                raise ValueError("Unknown victory mode.")
        elif key in STARTING_FIELDS:
            if not isinstance(value, dict) or set(value) != set(FACTIONS):
                raise ValueError(f"{key} requires all four factions.")
            for amount in value.values():
                _bounded(key, amount, 0, STARTING_FIELDS[key][1])
        else:
            _, low, high, _ = SCENARIO_FIELDS[key]
            _bounded(key, value, low, high)
            if key in INTEGER_FIELDS and type(value) is not int:
                raise ValueError(f"{key} must be an integer.")
        setattr(rules, key, value)
    if rules.victory_mode == "influence" and "victory_target" not in values:
        rules.victory_target = 250
    return rules


def _bounded(key, value, low, high):
    if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}.")


def default_ui(player="EU"):
    return {**DEFAULTS, "commander": player, "page": PAGES[0], "selected_front": FRONTS[0],
            "guide_enabled": True, "handoff": False, "review_open": False, "review_step": 0}


def ui_values(values):
    if not isinstance(values, dict) or not set(values) <= default_ui().keys() or not valid_preferences(values):
        raise ValueError("Invalid presentation preferences.")
    for key, value in values.items():
        choices = {"commander": FACTIONS, "page": PAGES, "selected_front": FRONTS}
        if key in choices and value not in choices[key]:
            raise ValueError(f"Invalid {key}.")
        if key in ("guide_enabled", "handoff", "review_open") and type(value) is not bool:
            raise ValueError(f"{key} must be a boolean.")
        if key == "review_step" and (type(value) is not int or not 0 <= value < len(PHASES)):
            raise ValueError("Invalid review step.")
    return values.copy()


@lru_cache(maxsize=1)
def catalog():
    opening = new_game()
    return {
        "investments": {key: {**asdict(spec), "kind": "building" if key in BUILDINGS else "project"}
                        for key, spec in INVESTMENTS.items()},
        "governments": list(GOVERNMENTS), "government_effects": GOVERNMENT_EFFECTS,
        "scenario": SCENARIO, "traits": TRAITS, "colors": COLORS,
        "objective_names": OBJECTIVE_NAMES, "pages": PAGES, "phases": PHASES,
        "opening_objectives": {f: objective_progress(opening, f) for f in FACTIONS},
        "defaults": asdict(Rules()),
        "scenario_fields": {key: {"label": label, "min": low, "max": high, "step": step,
                                   "integer": key in INTEGER_FIELDS}
                            for key, (label, low, high, step) in SCENARIO_FIELDS.items()},
        "starting_fields": {key: {"label": label, "max": high} for key, (label, high) in STARTING_FIELDS.items()},
    }


def command_view(game, forecast):
    factions = {}
    for faction in FACTIONS:
        nation, order = game.nations[faction], game.orders[faction]
        try:
            plan, error = preview_plan(game, faction), None
        except ValueError as exc:
            plan, error = None, str(exc)
        factions[faction] = {
            "plan": plan, "plan_error": error, "changes": changed_decisions(game, faction),
            "alerts": resource_alerts(game, faction, forecast),
            "objectives": objective_briefing(game, faction, forecast),
            "costs": {key: investment_cost(game, faction, key) for key in INVESTMENTS},
            "construction": forecast["factions"][faction]["construction"] if forecast else construction_rows(game, faction),
            "debt": game.debt(faction), "domestic_interest": domestic_interest(game, faction),
            "influence": game.influence(faction), "dominance_bonus": dominance_bonus(game, faction),
            "reserve": nation.military - sum(order.deployments.values()),
            "remaining_productivity": nation.productivity - sum(order.investments.values()),
        }
    review = None
    if game.reports:
        report = game.reports[-1]
        review = {"year": report["year"], "grouped": "phase_ends" in report,
                  "phases": [{"key": key, "name": name, "messages": phase_messages(report, key)} for key, name in PHASES.items()],
                  "highlights": {f: [{"message": report["messages"][i], "phase": message_phase(report, i)}
                                      for i in report.get("highlights", {}).get(f, [])] for f in FACTIONS}}
    return {"factions": factions, "fronts": {front: theater_snapshot(game, front) for front in FRONTS},
            "victory": victory_watch(game, forecast), "review": review}
